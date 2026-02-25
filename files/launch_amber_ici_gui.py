#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════╗
║   AMBER ICI // INVESTIGATIVE COMMAND INTERFACE v2    ║
║   Launches the local GUI in your default browser.    ║
║   NO cloud. NO telemetry. NO outbound requests.      ║
╚══════════════════════════════════════════════════════╝

Usage:
    python3 launch_amber_ici_gui.py [--port 8765] [--no-browser]

Options:
    --port        Port to serve the GUI on (default: 8765)
    --host        Host address (default: 127.0.0.1)
    --no-browser  Don't auto-open the browser
    --gui PATH    Path to GUI HTML (default: auto-detected)
"""

import argparse
import base64
import http.server
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.parse
import uuid
import webbrowser
import zipfile
from io import BytesIO
from pathlib import Path

# ── ANSI colors ────────────────────────────────────────────────────────────────
R  = "\033[0m"
BO = "\033[1m"
AM = "\033[38;5;214m"  # amber
GR = "\033[38;5;83m"   # green
DM = "\033[38;5;244m"  # dim
RD = "\033[38;5;196m"  # red
CY = "\033[38;5;117m"  # cyan

STORAGE_ROOT = None
STORE_DOMAINS = {"state", "agents", "chains", "vectors", "timeline"}
STORE_DIR = "state"
LEGACY_STORE_NAMES = {
    ("agents", "agents_state"): "agents_state",
    ("agents", "agent_sets"): "agent_sets",
    ("chains", "pipeline_state"): "pipeline_state",
    ("chains", "chain_sets"): "chain_sets",
    ("vectors", "vector_store"): "vector_store",
    ("timeline", "timeline_state"): "timeline_state",
}
MAX_UPLOAD_BYTES = 32 * 1024 * 1024
FILE_DOMAINS = {"txt", "md", "pdf", "docx"}
PDF_OCR_ENABLED = True
PDF_OCR_TIMEOUT_SEC = 300
PDF_OCR_MIN_CHARS = 240

def banner():
    print(f"""
{AM}{BO}
  █████╗ ███╗   ███╗██████╗ ███████╗██████╗
 ██╔══██╗████╗ ████║██╔══██╗██╔════╝██╔══██╗
 ███████║██╔████╔██║██████╔╝█████╗  ██████╔╝
 ██╔══██║██║╚██╔╝██║██╔══██╗██╔══╝  ██╔══██╗
 ██║  ██║██║ ╚═╝ ██║██████╔╝███████╗██║  ██║{R}
{DM}  INVESTIGATIVE COMMAND INTERFACE // LOCAL INFERENCE // NO TELEMETRY{R}
""")

def check_port_free(host, port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((host, port))
            return True
        except OSError:
            return False

def find_gui_file(hint=None):
    """Locate GUI HTML relative to this script or from a hint."""
    if hint:
        p = Path(hint)
        if p.exists() and p.is_file():
            return p
        print(f"{RD}ERROR:{R} GUI file not found: {hint}")
        sys.exit(1)

    # Search common locations and both legacy/current names
    names = ("amber_ui.html", "ici_gui.html", "ollama_gui.html", "index.html")
    roots = (Path(__file__).parent, Path(__file__).parent / "gui", Path.cwd())
    candidates = [r / n for r in roots for n in names]
    for c in candidates:
        if c.exists():
            return c

    print(f"{RD}ERROR:{R} Could not find a GUI HTML file.")
    print(f"{DM}  Searched for: {', '.join(names)}{R}")
    print(f"{DM}  Place one of these files in the same directory as this script.{R}")
    sys.exit(1)

class SilentHandler(http.server.SimpleHTTPRequestHandler):
    """Serve files silently (no request logs)."""
    def log_message(self, *_):
        pass

    def _send_json(self, status_code, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _store_path(self, domain, name):
        if domain not in STORE_DOMAINS:
            return None
        if not name.replace("_", "").replace("-", "").isalnum():
            return None
        root = Path(STORAGE_ROOT or Path.cwd())
        store_dir = root / STORE_DIR
        store_dir.mkdir(parents=True, exist_ok=True)
        if domain == "state":
            return store_dir / f"{name}.json"
        mapped = LEGACY_STORE_NAMES.get((domain, name))
        if not mapped:
            return None
        return store_dir / f"{mapped}.json"

    def _uploads_root(self):
        root = Path(STORAGE_ROOT or Path.cwd()) / "uploads"
        (root / "blobs").mkdir(parents=True, exist_ok=True)
        (root / "texts").mkdir(parents=True, exist_ok=True)
        return root

    def _manifest_path(self):
        return self._uploads_root() / "manifest.json"

    def _load_manifest(self):
        p = self._manifest_path()
        if not p.exists():
            return []
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except Exception:
            return []

    def _save_manifest(self, entries):
        p = self._manifest_path()
        tmp = p.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(entries, ensure_ascii=True, indent=2), encoding="utf-8")
        tmp.replace(p)

    def _safe_name(self, name):
        base = Path(str(name or "file")).name
        base = re.sub(r"[^A-Za-z0-9._-]+", "_", base).strip("._")
        return base or "file"

    def _decode_text_bytes(self, raw):
        for enc in ("utf-8", "utf-16", "latin1"):
            try:
                return raw.decode(enc)
            except Exception:
                continue
        return raw.decode("latin1", errors="ignore")

    def _extract_pdf_text_basic(self, raw):
        text = raw.decode("latin1", errors="ignore")
        blocks = re.findall(r"BT[\s\S]*?ET", text)
        out = []
        for block in blocks:
            for tok in re.findall(r"\(([^)]*)\)\s*Tj", block):
                out.append(tok)
        return " ".join(out).strip()

    def _extract_pdf_text_ocr(self, raw):
        if not PDF_OCR_ENABLED:
            return ""
        if shutil.which("ocrmypdf") is None:
            return ""
        try:
            with tempfile.TemporaryDirectory(prefix="amber_pdf_ocr_") as td:
                tdir = Path(td)
                inp = tdir / "input.pdf"
                outp = tdir / "output.pdf"
                sidecar = tdir / "sidecar.txt"
                inp.write_bytes(raw)
                cmd = [
                    "ocrmypdf",
                    "--force-ocr",
                    "--quiet",
                    "--sidecar", str(sidecar),
                    str(inp),
                    str(outp),
                ]
                run = subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=PDF_OCR_TIMEOUT_SEC,
                    check=False,
                )
                if run.returncode != 0:
                    return ""
                if not sidecar.exists():
                    return ""
                txt = sidecar.read_text(encoding="utf-8", errors="ignore").strip()
                return txt
        except Exception:
            return ""

    def _extract_pdf_text(self, raw):
        basic = self._extract_pdf_text_basic(raw)
        ocr = self._extract_pdf_text_ocr(raw)
        if ocr and len(ocr) >= max(PDF_OCR_MIN_CHARS, int(len(basic) * 1.15)):
            return ocr
        if basic:
            return basic
        if ocr:
            return ocr
        return "[PDF: extraction unavailable]"

    def _extract_docx_text(self, raw):
        try:
            with zipfile.ZipFile(BytesIO(raw)) as zf:
                xml = zf.read("word/document.xml").decode("utf-8", errors="ignore")
        except Exception:
            return "[DOCX: extraction unavailable]"
        parts = re.findall(r"<w:t[^>]*>(.*?)</w:t>", xml)
        cleaned = []
        for part in parts:
            cleaned.append(re.sub(r"<[^>]+>", "", part))
        joined = " ".join(cleaned).strip()
        return joined or "[DOCX: extraction unavailable]"

    def _extract_text(self, ext, raw):
        ext = ext.lower().lstrip(".")
        if ext in {"txt", "md"}:
            return self._decode_text_bytes(raw)
        if ext == "pdf":
            return self._extract_pdf_text(raw)
        if ext == "docx":
            return self._extract_docx_text(raw)
        return ""

    def _files_list(self):
        entries = self._load_manifest()
        pub = []
        for e in entries:
            pub.append({
                "id": e.get("id"),
                "name": e.get("name"),
                "size": e.get("size", 0),
                "ext": e.get("ext", ""),
                "chars": e.get("chars", 0),
                "uploaded_at": e.get("uploaded_at", "")
            })
        self._send_json(200, {"ok": True, "files": pub})

    def _files_upload(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length) if length > 0 else b"{}"
            payload = json.loads(raw.decode("utf-8"))
        except Exception:
            self._send_json(400, {"ok": False, "error": "invalid json payload"})
            return

        name = str(payload.get("name", "")).strip()
        data_b64 = str(payload.get("data_b64", "")).strip()
        if not name or not data_b64:
            self._send_json(400, {"ok": False, "error": "name and data_b64 required"})
            return
        safe_name = self._safe_name(name)
        ext = Path(safe_name).suffix.lower().lstrip(".")
        if ext not in FILE_DOMAINS:
            self._send_json(400, {"ok": False, "error": f"unsupported extension: .{ext}"})
            return
        try:
            raw_bytes = base64.b64decode(data_b64.encode("ascii"), validate=True)
        except Exception:
            self._send_json(400, {"ok": False, "error": "invalid base64 data"})
            return
        if len(raw_bytes) > MAX_UPLOAD_BYTES:
            self._send_json(400, {"ok": False, "error": f"file exceeds {MAX_UPLOAD_BYTES} bytes"})
            return

        file_id = uuid.uuid4().hex[:12].upper()
        root = self._uploads_root()
        blob_rel = f"uploads/blobs/{file_id}_{safe_name}"
        text_rel = f"uploads/texts/{file_id}.txt"
        blob_path = Path(STORAGE_ROOT or Path.cwd()) / blob_rel
        text_path = Path(STORAGE_ROOT or Path.cwd()) / text_rel

        text_content = self._extract_text(ext, raw_bytes)
        blob_path.write_bytes(raw_bytes)
        text_path.write_text(text_content, encoding="utf-8")

        manifest = self._load_manifest()
        entry = {
            "id": file_id,
            "name": name,
            "safe_name": safe_name,
            "size": len(raw_bytes),
            "ext": ext,
            "chars": len(text_content),
            "blob_path": blob_rel,
            "text_path": text_rel,
            "uploaded_at": time.strftime("%Y-%m-%dT%H:%M:%S")
        }
        manifest.append(entry)
        self._save_manifest(manifest)
        self._send_json(200, {"ok": True, "entry": {
            "id": entry["id"],
            "name": entry["name"],
            "size": entry["size"],
            "ext": entry["ext"],
            "chars": entry["chars"],
            "uploaded_at": entry["uploaded_at"]
        }})

    def _files_context(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length) if length > 0 else b"{}"
            payload = json.loads(raw.decode("utf-8"))
            ids = payload.get("ids", [])
            if not isinstance(ids, list):
                raise ValueError("ids must be list")
        except Exception:
            self._send_json(400, {"ok": False, "error": "invalid payload"})
            return

        wanted = {str(x) for x in ids}
        manifest = self._load_manifest()
        parts = []
        count = 0
        total_chars = 0
        for e in manifest:
            file_id = str(e.get("id", ""))
            if file_id not in wanted:
                continue
            text_rel = e.get("text_path", "")
            if not text_rel:
                continue
            p = Path(STORAGE_ROOT or Path.cwd()) / text_rel
            if not p.exists():
                continue
            try:
                txt = p.read_text(encoding="utf-8")
            except Exception:
                continue
            parts.append(f"[FILE: {e.get('name','UNKNOWN')}]\n{txt}")
            count += 1
            total_chars += len(txt)

        self._send_json(200, {"ok": True, "context": "\n\n".join(parts), "files": count, "chars": total_chars})

    def _files_read(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length) if length > 0 else b"{}"
            payload = json.loads(raw.decode("utf-8"))
            ids = payload.get("ids", [])
            if not isinstance(ids, list):
                raise ValueError("ids must be list")
        except Exception:
            self._send_json(400, {"ok": False, "error": "invalid payload"})
            return

        wanted = {str(x) for x in ids}
        manifest = self._load_manifest()
        docs = []
        for e in manifest:
            file_id = str(e.get("id", ""))
            if wanted and file_id not in wanted:
                continue
            text_rel = e.get("text_path", "")
            if not text_rel:
                continue
            p = Path(STORAGE_ROOT or Path.cwd()) / text_rel
            if not p.exists():
                continue
            try:
                txt = p.read_text(encoding="utf-8")
            except Exception:
                continue
            docs.append({
                "id": file_id,
                "name": e.get("name", "UNKNOWN"),
                "ext": e.get("ext", ""),
                "size": e.get("size", 0),
                "chars": e.get("chars", len(txt)),
                "text": txt
            })

        self._send_json(200, {"ok": True, "docs": docs})

    def _files_delete(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length) if length > 0 else b"{}"
            payload = json.loads(raw.decode("utf-8"))
            file_id = str(payload.get("id", "")).strip()
        except Exception:
            self._send_json(400, {"ok": False, "error": "invalid payload"})
            return
        if not file_id:
            self._send_json(400, {"ok": False, "error": "id required"})
            return

        manifest = self._load_manifest()
        kept = []
        removed = False
        for e in manifest:
            if str(e.get("id", "")) != file_id:
                kept.append(e)
                continue
            removed = True
            for rel in (e.get("blob_path", ""), e.get("text_path", "")):
                p = Path(STORAGE_ROOT or Path.cwd()) / rel
                if p.exists():
                    try:
                        p.unlink()
                    except Exception:
                        pass
        if removed:
            self._save_manifest(kept)
            self._send_json(200, {"ok": True})
            return
        self._send_json(404, {"ok": False, "error": "file id not found"})

    def _store_get(self, domain, name):
        path = self._store_path(domain, name)
        if not path:
            self._send_json(400, {"ok": False, "error": "invalid store path"})
            return
        if not path.exists():
            self._send_json(200, {"ok": True, "data": []})
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            self._send_json(500, {"ok": False, "error": "store read failed"})
            return
        self._send_json(200, {"ok": True, "data": data})

    def _store_set(self, domain, name):
        path = self._store_path(domain, name)
        if not path:
            self._send_json(400, {"ok": False, "error": "invalid store path"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length) if length > 0 else b"null"
            data = json.loads(raw.decode("utf-8"))
        except Exception:
            self._send_json(400, {"ok": False, "error": "invalid json payload"})
            return
        try:
            tmp_path = path.with_suffix(".json.tmp")
            tmp_path.write_text(json.dumps(data, ensure_ascii=True, indent=2), encoding="utf-8")
            tmp_path.replace(path)
        except Exception:
            self._send_json(500, {"ok": False, "error": "store write failed"})
            return
        self._send_json(200, {"ok": True})

    def do_GET(self):
        parts = urllib.parse.urlparse(self.path)
        seg = [s for s in parts.path.split("/") if s]
        if len(seg) == 4 and seg[0] == "api" and seg[1] == "store":
            self._store_get(seg[2], seg[3])
            return
        if seg == ["api", "files", "list"]:
            self._files_list()
            return
        super().do_GET()

    def do_POST(self):
        parts = urllib.parse.urlparse(self.path)
        seg = [s for s in parts.path.split("/") if s]
        if len(seg) == 4 and seg[0] == "api" and seg[1] == "store":
            self._store_set(seg[2], seg[3])
            return
        if seg == ["api", "files", "upload"]:
            self._files_upload()
            return
        if seg == ["api", "files", "context"]:
            self._files_context()
            return
        if seg == ["api", "files", "read"]:
            self._files_read()
            return
        if seg == ["api", "files", "delete"]:
            self._files_delete()
            return
        self._send_json(404, {"ok": False, "error": "not found"})

    def end_headers(self):
        # Strict no-cache, no external calls
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Permissions-Policy", "camera=(), microphone=(), geolocation=(), payment=(), usb=()")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; "
            "connect-src http://127.0.0.1:* http://localhost:*; "
            "img-src 'self' data: blob:; "
            "style-src 'self' 'unsafe-inline'; "
            "script-src 'self' 'unsafe-inline'; "
            "font-src 'self' data:; "
            "object-src 'none'; base-uri 'self'; form-action 'none'; frame-ancestors 'none'"
        )
        super().end_headers()

def launch(host, port, gui_path, open_browser):
    gui_path = Path(gui_path).resolve()
    gui_dir = gui_path.parent
    gui_file = gui_path.name
    project_root = gui_dir.parent

    global STORAGE_ROOT
    STORAGE_ROOT = str(project_root)
    state_dir = Path(STORAGE_ROOT) / STORE_DIR
    state_dir.mkdir(parents=True, exist_ok=True)
    legacy_dirs = [
        Path(STORAGE_ROOT) / "agents",
        Path(STORAGE_ROOT) / "chains",
        Path(STORAGE_ROOT) / "vectors",
        Path(STORAGE_ROOT) / "timeline",
        gui_dir / "agents",
        gui_dir / "chains",
        gui_dir / "vectors",
        gui_dir / "timeline",
    ]
    for legacy in legacy_dirs:
        if not legacy.exists() or not legacy.is_dir():
            continue
        for src in legacy.glob("*.json"):
            dst = state_dir / src.name
            if dst.exists():
                continue
            try:
                src.replace(dst)
            except Exception:
                pass
        # Remove duplicate folders only when empty.
        try:
            legacy.rmdir()
        except Exception:
            pass

    os.chdir(gui_dir)

    if not check_port_free(host, port):
        print(f"{RD}✗{R} Port {port} is already in use. Try --port XXXX")
        sys.exit(1)

    server = http.server.HTTPServer((host, port), SilentHandler)
    url = f"http://{host}:{port}/{gui_file}"

    print(f"  {GR}●{R} Server   : {AM}{url}{R}")
    print(f"  {GR}●{R} GUI file : {DM}{gui_path}{R}")
    print(f"  {GR}●{R} Ollama   : {DM}http://127.0.0.1:11434  (localhost only){R}")
    print(f"  {GR}●{R} Stores   : {DM}{STORAGE_ROOT}/{STORE_DIR}/*.json{R}")
    print(f"  {GR}●{R} Uploads  : {DM}{STORAGE_ROOT}/uploads/[blobs|texts]{R}")
    print(f"\n  {DM}Press CTRL+C to stop{R}\n")
    print(f"  {DM}{'─'*52}{R}")

    if open_browser:
        def _open():
            time.sleep(0.6)
            webbrowser.open(url)
        threading.Thread(target=_open, daemon=True).start()
        print(f"  {GR}→{R} Opening browser...")
    else:
        print(f"  {CY}→{R} Navigate to: {AM}{url}{R}")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print(f"\n\n  {AM}◼{R} Server stopped. Goodbye.")
        server.server_close()

def main():
    banner()
    parser = argparse.ArgumentParser(
        description="Launch the Investigative Command Interface (AMBER ICI) in your browser",
        add_help=True
    )
    parser.add_argument("--port", type=int, default=8765,
                        help="Port to serve on (default: 8765)")
    parser.add_argument("--host", default="127.0.0.1",
                        help="Host address (default: 127.0.0.1)")
    parser.add_argument("--no-browser", action="store_true",
                        help="Don't auto-open browser")
    parser.add_argument("--gui", default=None,
                        help="Path to GUI HTML (e.g. files/amber_ui.html)")
    args = parser.parse_args()

    gui_path = find_gui_file(args.gui)

    print(f"  {AM}INVESTIGATIVE COMMAND INTERFACE LAUNCHER{R}\n")
    launch(args.host, args.port, gui_path, not args.no_browser)

if __name__ == "__main__":
    main()
