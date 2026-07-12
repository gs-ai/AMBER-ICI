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
import hashlib
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
import webbrowser
import zipfile
from io import BytesIO
from pathlib import Path
from constrained_executor import ContractError, execute_contract
from autogen_builder import AutoGenError, build_autogen_plan

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
LINKED_TEXT_EXTS = {
    "txt", "md", "py", "js", "ts", "tsx", "jsx", "json", "yaml", "yml",
    "toml", "ini", "cfg", "conf", "xml", "html", "css", "sql", "sh",
    "bash", "zsh", "log", "csv", "tsv", "rtf"
}
LINKED_IMAGE_OCR_EXTS = {"png", "jpg", "jpeg", "bmp", "webp", "tif", "tiff"}
LINKED_SPREADSHEET_EXTS = {"xlsx", "xls", "ods"}
LINKED_BINARY_LABEL_EXTS = {
    "gif", "svg", "heic", "ico", "ppt", "pptx", "zip"
}
LINKED_ALLOWED_EXTS = LINKED_TEXT_EXTS | LINKED_IMAGE_OCR_EXTS | LINKED_SPREADSHEET_EXTS | LINKED_BINARY_LABEL_EXTS | {"pdf", "docx"}
MAX_UPLOAD_BYTES = 100 * 1024 * 1024
MAX_JSON_BODY_BYTES = int(MAX_UPLOAD_BYTES * 1.4) + 4096
PDF_OCR_ENABLED = True
PDF_OCR_TIMEOUT_SEC = 300
PDF_OCR_MIN_CHARS = 240
IMAGE_OCR_TIMEOUT_SEC = 120
IMAGE_OCR_MIN_CHARS = 8

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
    _CLIENT_DISCONNECT_ERRORS = (BrokenPipeError, ConnectionResetError, ConnectionAbortedError)

    def log_message(self, format, *args):
        pass

    def _send_json(self, status_code, payload):
        body = json.dumps(payload).encode("utf-8")
        try:
            self.send_response(status_code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except self._CLIENT_DISCONNECT_ERRORS:
            # Browser may cancel in-flight polling requests; treat as benign.
            return

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
        root.mkdir(parents=True, exist_ok=True)
        (root / "blobs").mkdir(parents=True, exist_ok=True)
        (root / "texts").mkdir(parents=True, exist_ok=True)
        try:
            root.chmod(0o700)
            (root / "blobs").chmod(0o700)
            (root / "texts").chmod(0o700)
        except Exception:
            pass
        return root

    def _manifest_path(self):
        return self._uploads_root() / "manifest.json"

    def _linked_dir_state_path(self):
        root = Path(STORAGE_ROOT or Path.cwd())
        state_dir = root / STORE_DIR
        state_dir.mkdir(parents=True, exist_ok=True)
        return state_dir / "linked_dir_state.json"

    def _load_linked_dir(self):
        p = self._linked_dir_state_path()
        if not p.exists():
            return None
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            linked = str(data.get("path", "")).strip()
            if not linked:
                return None
            d = Path(linked).expanduser().resolve()
            return d if d.exists() and d.is_dir() else None
        except Exception:
            return None

    def _save_linked_dir(self, path_obj):
        p = self._linked_dir_state_path()
        payload = {"path": str(path_obj.resolve()), "linked_at": time.strftime("%Y-%m-%dT%H:%M:%S")}
        tmp = p.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")
        tmp.replace(p)

    def _file_id_for_linked(self, rel_name):
        digest = hashlib.sha1(rel_name.encode("utf-8", errors="ignore")).hexdigest()[:12].upper()
        return f"LD_{digest}"

    def _file_id_for_upload(self, safe_name, raw):
        h = hashlib.sha1()
        h.update(safe_name.encode("utf-8", errors="ignore"))
        h.update(b"\0")
        h.update(raw[:1024 * 1024])
        h.update(str(len(raw)).encode("ascii"))
        return f"UP_{h.hexdigest()[:16].upper()}"

    def _is_visible(self, path_obj):
        name = path_obj.name
        return bool(name) and not name.startswith(".")

    def _safe_rel_under(self, root_dir, candidate):
        try:
            root_resolved = root_dir.resolve()
            cand_resolved = candidate.resolve()
            cand_resolved.relative_to(root_resolved)
            return True
        except Exception:
            return False

    def _iter_linked_entries(self):
        linked = self._load_linked_dir()
        if not linked:
            return None, []
        entries = []
        for child in sorted(linked.iterdir(), key=lambda p: p.name.lower()):
            if not child.is_file():
                continue
            if not self._is_visible(child):
                continue
            if not self._safe_rel_under(linked, child):
                continue
            ext = child.suffix.lower().lstrip(".")
            if ext not in LINKED_ALLOWED_EXTS:
                continue
            try:
                st = child.stat()
            except Exception:
                continue
            rel_name = child.name
            entries.append({
                "id": self._file_id_for_linked(rel_name),
                "name": rel_name,
                "safe_name": rel_name,
                "size": int(st.st_size),
                "ext": ext,
                "chars": 0,
                "abs_path": str(child.resolve()),
                "uploaded_at": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(st.st_mtime)),
                "source": "linked_dir",
            })
        return linked, entries

    def _extract_xlsx_text(self, raw):
        try:
            with zipfile.ZipFile(BytesIO(raw)) as zf:
                shared = []
                if "xl/sharedStrings.xml" in zf.namelist():
                    sxml = zf.read("xl/sharedStrings.xml").decode("utf-8", errors="ignore")
                    shared = re.findall(r"<t[^>]*>(.*?)</t>", sxml)
                out_rows = []
                for name in zf.namelist():
                    if not re.match(r"xl/worksheets/sheet\d+\.xml$", name):
                        continue
                    xml = zf.read(name).decode("utf-8", errors="ignore")
                    rows = re.findall(r"<row[^>]*>([\s\S]*?)</row>", xml)
                    for row in rows:
                        cells = re.findall(r"<c[^>]*>([\s\S]*?)</c>", row)
                        vals = []
                        for cell in cells:
                            vm = re.search(r"<v>(.*?)</v>", cell)
                            if not vm:
                                vals.append("")
                                continue
                            v = vm.group(1)
                            if ' t="s"' in cell:
                                try:
                                    idx = int(v)
                                    vals.append(shared[idx] if 0 <= idx < len(shared) else v)
                                except Exception:
                                    vals.append(v)
                            else:
                                vals.append(v)
                        if any(x.strip() for x in vals):
                            out_rows.append("\t".join(vals))
                txt = "\n".join(out_rows).strip()
                return txt if txt else "[SPREADSHEET: no readable cells found]"
        except Exception:
            return "[SPREADSHEET: extraction unavailable]"

    def _load_manifest(self):
        p = self._manifest_path()
        if not p.exists():
            return []
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except Exception:
            return []

    def _uploaded_entries(self):
        entries = []
        blobs = self._uploads_root() / "blobs"
        texts = self._uploads_root() / "texts"
        for item in self._load_manifest():
            if not isinstance(item, dict):
                continue
            fid = str(item.get("id", "")).strip()
            name = str(item.get("name", "")).strip()
            ext = str(item.get("ext", "")).lower().strip()
            blob_name = str(item.get("blob", "")).strip()
            text_name = str(item.get("text", "")).strip()
            if not fid or not name or ext not in LINKED_ALLOWED_EXTS:
                continue
            blob_path = blobs / blob_name
            text_path = texts / text_name if text_name else None
            if not blob_name or not blob_path.exists() or not self._safe_rel_under(blobs, blob_path):
                continue
            if text_path and (not text_path.exists() or not self._safe_rel_under(texts, text_path)):
                text_path = None
            entry = {
                "id": fid,
                "name": name,
                "safe_name": item.get("safe_name") or self._safe_name(name),
                "size": int(item.get("size") or 0),
                "ext": ext,
                "chars": int(item.get("chars") or 0),
                "abs_path": str(blob_path.resolve()),
                "text_path": str(text_path.resolve()) if text_path else "",
                "uploaded_at": item.get("uploaded_at", ""),
                "source": "upload",
            }
            entries.append(entry)
        return entries

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

    def _extract_svg_text(self, raw):
        try:
            txt = raw.decode("utf-8", errors="ignore")
            parts = re.findall(r"<(?:text|tspan)[^>]*>([\s\S]*?)</(?:text|tspan)>", txt, flags=re.I)
            cleaned = [re.sub(r"<[^>]+>", " ", p) for p in parts]
            joined = re.sub(r"\s+", " ", " ".join(cleaned)).strip()
            return joined or "[SVG: no embedded text found]"
        except Exception:
            return "[SVG: text extraction unavailable]"

    def _prepare_ocr_image(self, raw, ext, tdir):
        src = tdir / f"input.{ext if ext else 'img'}"
        src.write_bytes(raw)
        if ext in {"png", "jpg", "jpeg", "tif", "tiff", "bmp"}:
            return src
        try:
            from PIL import Image
            out = tdir / "input.png"
            with Image.open(BytesIO(raw)) as im:
                im.convert("RGB").save(out, format="PNG")
            return out
        except Exception:
            return src

    def _extract_image_text_ocr(self, raw, ext):
        if shutil.which("tesseract") is None:
            return "[IMAGE: OCR unavailable - tesseract not installed]"
        ext = ext.lower().lstrip(".")
        best = ""
        try:
            with tempfile.TemporaryDirectory(prefix="amber_img_ocr_") as td:
                tdir = Path(td)
                img = self._prepare_ocr_image(raw, ext, tdir)
                for psm in ("6", "11"):
                    cmd = ["tesseract", str(img), "stdout", "--dpi", "300", "--psm", psm]
                    run = subprocess.run(
                        cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        timeout=IMAGE_OCR_TIMEOUT_SEC,
                        check=False,
                    )
                    if run.returncode != 0:
                        continue
                    txt = re.sub(r"[ \t]+\n", "\n", run.stdout).strip()
                    txt = re.sub(r"\n{4,}", "\n\n\n", txt)
                    if len(txt) > len(best):
                        best = txt
                    if len(best) >= IMAGE_OCR_MIN_CHARS:
                        break
        except Exception:
            best = ""
        return best if best else "[IMAGE: OCR found no readable text]"

    def _extract_text(self, ext, raw):
        ext = ext.lower().lstrip(".")
        if ext in LINKED_TEXT_EXTS:
            return self._decode_text_bytes(raw)
        if ext == "pdf":
            return self._extract_pdf_text(raw)
        if ext == "docx":
            return self._extract_docx_text(raw)
        if ext in LINKED_SPREADSHEET_EXTS:
            return self._extract_xlsx_text(raw)
        if ext in LINKED_IMAGE_OCR_EXTS:
            return self._extract_image_text_ocr(raw, ext)
        if ext == "svg":
            return self._extract_svg_text(raw)
        return ""

    def _extract_text_for_linked(self, entry):
        abs_path = Path(entry.get("abs_path", ""))
        if not abs_path.exists() or not abs_path.is_file():
            return ""
        ext = str(entry.get("ext", "")).lower()
        try:
            raw = abs_path.read_bytes()
        except Exception:
            return ""
        if ext in LINKED_BINARY_LABEL_EXTS:
            return f"[BINARY FILE: {entry.get('name','UNKNOWN')} | .{ext} | {len(raw)} bytes]"
        txt = self._extract_text(ext, raw)
        return txt if txt else f"[FILE: {entry.get('name','UNKNOWN')} | .{ext} | no text extraction available]"

    def _extract_text_for_upload(self, entry):
        text_path = Path(str(entry.get("text_path", "")))
        if text_path.exists() and text_path.is_file():
            try:
                return text_path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                return ""
        abs_path = Path(str(entry.get("abs_path", "")))
        try:
            raw = abs_path.read_bytes()
        except Exception:
            return ""
        ext = str(entry.get("ext", "")).lower()
        if ext in LINKED_BINARY_LABEL_EXTS:
            return f"[BINARY FILE: {entry.get('name','UNKNOWN')} | .{entry.get('ext','')} | {len(raw)} bytes]"
        txt = self._extract_text(ext, raw)
        return txt if txt else f"[FILE: {entry.get('name','UNKNOWN')} | .{ext} | no text extraction available]"

    def _all_file_entries(self):
        linked, linked_entries = self._iter_linked_entries()
        return linked, self._uploaded_entries() + linked_entries

    def _entry_text(self, entry):
        if entry.get("source") == "upload":
            return self._extract_text_for_upload(entry)
        return self._extract_text_for_linked(entry)

    def _files_list(self):
        linked, entries = self._all_file_entries()
        linked_path = str(linked.resolve()) if linked else None
        pub = []
        for e in entries:
            pub.append({
                "id": e.get("id"),
                "name": e.get("name"),
                "size": e.get("size", 0),
                "ext": e.get("ext", ""),
                # Listing must stay metadata-only; extraction/OCR happens on explicit read/context calls.
                "chars": int(e.get("chars") or 0),
                "source": e.get("source", "linked_dir"),
                "uploaded_at": e.get("uploaded_at", "")
            })
        self._send_json(200, {"ok": True, "files": pub, "linked_dir": linked_path})

    def _files_link_dir(self):
        manual_path = ""
        try:
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length) if length > 0 else b"{}"
            payload = json.loads(raw.decode("utf-8"))
            manual_path = str((payload or {}).get("path", "")).strip()
        except Exception:
            manual_path = ""
        chosen = None
        if manual_path:
            chosen = manual_path
        else:
            try:
                import tkinter as tk
                from tkinter import filedialog
                root = tk.Tk()
                root.withdraw()
                root.attributes("-topmost", True)
                chosen = filedialog.askdirectory(title="AMBER ICI: Select directory for model file access")
                root.destroy()
            except Exception:
                chosen = None
        if not chosen:
            self._send_json(400, {"ok": False, "error": "directory selection canceled or unavailable"})
            return
        d = Path(chosen).expanduser().resolve()
        if not d.exists() or not d.is_dir():
            self._send_json(400, {"ok": False, "error": "selected path is not a directory"})
            return
        self._save_linked_dir(d)
        self._send_json(200, {"ok": True, "linked_dir": str(d)})

    def _files_linked_dir_get(self):
        linked = self._load_linked_dir()
        self._send_json(200, {"ok": True, "linked_dir": str(linked.resolve()) if linked else None})

    def _files_unlink_dir(self):
        p = self._linked_dir_state_path()
        try:
            if p.exists():
                p.unlink()
            self._send_json(200, {"ok": True, "linked_dir": None})
        except Exception:
            self._send_json(500, {"ok": False, "error": "failed to unlink directory"})

    def _files_upload(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > MAX_JSON_BODY_BYTES:
                self._send_json(413, {"ok": False, "error": "upload payload is too large"})
                return
            raw_body = self.rfile.read(length)
            payload = json.loads(raw_body.decode("utf-8"))
            name = str(payload.get("name", "")).strip()
            data_b64 = str(payload.get("data_b64", ""))
        except Exception:
            self._send_json(400, {"ok": False, "error": "invalid upload payload"})
            return
        safe_name = self._safe_name(name)
        ext = safe_name.rsplit(".", 1)[-1].lower() if "." in safe_name else ""
        if ext not in LINKED_ALLOWED_EXTS:
            self._send_json(415, {"ok": False, "error": f"unsupported file extension: .{ext or 'unknown'}"})
            return
        try:
            raw = base64.b64decode(data_b64, validate=True)
        except Exception:
            self._send_json(400, {"ok": False, "error": "invalid base64 file data"})
            return
        if len(raw) > MAX_UPLOAD_BYTES:
            self._send_json(413, {"ok": False, "error": "file exceeds 100MB upload limit"})
            return
        file_id = self._file_id_for_upload(safe_name, raw)
        root = self._uploads_root()
        blob_name = f"{file_id}_{safe_name}"
        text_name = f"{file_id}.txt"
        blob_path = root / "blobs" / blob_name
        text_path = root / "texts" / text_name
        try:
            blob_path.write_bytes(raw)
            try:
                blob_path.chmod(0o600)
            except Exception:
                pass
            if ext in LINKED_BINARY_LABEL_EXTS:
                text = f"[BINARY FILE: {safe_name} | .{ext} | {len(raw)} bytes]"
            else:
                text = self._extract_text(ext, raw)
                if not text:
                    text = f"[FILE: {safe_name} | .{ext} | no text extraction available]"
            text_path.write_text(text, encoding="utf-8", errors="ignore")
            try:
                text_path.chmod(0o600)
            except Exception:
                pass
            entry = {
                "id": file_id,
                "name": safe_name,
                "safe_name": safe_name,
                "blob": blob_name,
                "text": text_name,
                "size": len(raw),
                "ext": ext,
                "chars": len(text),
                "uploaded_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "source": "upload",
            }
            manifest = [e for e in self._load_manifest() if not isinstance(e, dict) or e.get("id") != file_id]
            manifest.append(entry)
            self._save_manifest(manifest)
        except Exception as e:
            for orphan in (blob_path, text_path):
                try:
                    if orphan.exists():
                        orphan.unlink()
                except Exception:
                    pass
            self._send_json(500, {"ok": False, "error": f"failed to store upload: {e}"})
            return
        self._send_json(200, {"ok": True, "entry": entry})

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
        _, manifest = self._all_file_entries()
        parts = []
        count = 0
        total_chars = 0
        for e in manifest:
            file_id = str(e.get("id", ""))
            if file_id not in wanted:
                continue
            txt = self._entry_text(e)
            if not txt:
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
        _, manifest = self._all_file_entries()
        docs = []
        for e in manifest:
            file_id = str(e.get("id", ""))
            if wanted and file_id not in wanted:
                continue
            txt = self._entry_text(e)
            if not txt:
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
            ids = payload.get("ids", [])
            if isinstance(ids, str):
                ids = [ids]
            wanted = {str(x) for x in ids}
        except Exception:
            self._send_json(400, {"ok": False, "error": "invalid payload"})
            return
        if not wanted:
            self._send_json(400, {"ok": False, "error": "no file ids provided"})
            return
        root = self._uploads_root()
        kept = []
        removed = 0
        for entry in self._load_manifest():
            if not isinstance(entry, dict) or str(entry.get("id", "")) not in wanted:
                kept.append(entry)
                continue
            for folder, key in (("blobs", "blob"), ("texts", "text")):
                name = str(entry.get(key, "")).strip()
                p = root / folder / name
                if name and self._safe_rel_under(root / folder, p):
                    try:
                        p.unlink(missing_ok=True)
                    except Exception:
                        pass
            removed += 1
        self._save_manifest(kept)
        self._send_json(200, {"ok": True, "removed": removed})

    def _vectors_path(self):
        path = self._store_path("vectors", "vector_store")
        if path:
            path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def _load_vectors(self):
        path = self._vectors_path()
        if not path or not path.exists():
            return []
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                data = data.get("chunks", [])
            return data if isinstance(data, list) else []
        except Exception:
            return []

    def _save_vectors(self, chunks):
        path = self._vectors_path()
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(chunks, ensure_ascii=True), encoding="utf-8")
        tmp.replace(path)

    def _vector_get(self):
        self._send_json(200, {"ok": True, "chunks": self._load_vectors()})

    def _vector_import(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length) if length > 0 else b"{}"
            payload = json.loads(raw.decode("utf-8"))
            chunks = payload.get("chunks", [])
            if not isinstance(chunks, list):
                raise ValueError("chunks must be list")
        except Exception:
            self._send_json(400, {"ok": False, "error": "invalid vector payload"})
            return
        merged = {str(c.get("id", i)): c for i, c in enumerate(self._load_vectors()) if isinstance(c, dict)}
        for i, chunk in enumerate(chunks):
            if isinstance(chunk, dict):
                merged[str(chunk.get("id", f"import_{i}"))] = chunk
        out = list(merged.values())
        self._save_vectors(out)
        self._send_json(200, {"ok": True, "chunks": len(out)})

    def _vector_save_doc(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length) if length > 0 else b"{}"
            payload = json.loads(raw.decode("utf-8"))
            filename = str(payload.get("filename", "")).strip()
            source = str(payload.get("source", "file")).strip() or "file"
            chunks = payload.get("chunks", [])
            if not filename or not isinstance(chunks, list):
                raise ValueError("invalid save payload")
        except Exception:
            self._send_json(400, {"ok": False, "error": "invalid vector save payload"})
            return
        kept = [
            c for c in self._load_vectors()
            if not (isinstance(c, dict) and c.get("filename") == filename and str(c.get("source", "file")) == source)
        ]
        kept.extend(c for c in chunks if isinstance(c, dict))
        self._save_vectors(kept)
        self._send_json(200, {"ok": True, "chunks": len(kept)})

    def _vector_delete_doc(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length) if length > 0 else b"{}"
            payload = json.loads(raw.decode("utf-8"))
            filename = str(payload.get("filename", "")).strip()
            source = str(payload.get("source", "file")).strip() or "file"
        except Exception:
            filename = ""
            source = "file"
        if not filename:
            self._send_json(400, {"ok": False, "error": "filename required"})
            return
        kept = [
            c for c in self._load_vectors()
            if not (isinstance(c, dict) and c.get("filename") == filename and str(c.get("source", "file")) == source)
        ]
        self._save_vectors(kept)
        self._send_json(200, {"ok": True, "chunks": len(kept)})

    def _vector_clear(self):
        self._save_vectors([])
        self._send_json(200, {"ok": True, "chunks": 0})

    def _web_cache_path(self):
        path = self._store_path("state", "web_cache")
        if path:
            path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def _load_web_cache(self):
        path = self._web_cache_path()
        if not path or not path.exists():
            return {}
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _save_web_cache(self, cache):
        path = self._web_cache_path()
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(cache, ensure_ascii=True), encoding="utf-8")
        tmp.replace(path)

    def _web_fetch(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length) if length > 0 else b"{}"
            payload = json.loads(raw.decode("utf-8"))
            query = str(payload.get("query", "")).strip()
        except Exception:
            self._send_json(400, {"ok": False, "error": "invalid web fetch payload"})
            return
        parsed = urllib.parse.urlparse(query)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            self._send_json(400, {"ok": False, "error": "WEB fetch requires an explicit http(s) URL"})
            return
        cache_key = hashlib.sha1(query.encode("utf-8", errors="ignore")).hexdigest()
        cache = self._load_web_cache()
        now = time.time()
        cached = cache.get(cache_key)
        if isinstance(cached, dict) and now - float(cached.get("ts", 0)) < 3600:
            self._send_json(200, {"ok": True, "cached": True, "url": query, "content": cached.get("content", "")})
            return
        text = self._web_fetch_playwright(query)
        if text is None:
            text = self._web_fetch_urllib(query)
        if text is None:
            self._send_json(502, {"ok": False, "error": "web fetch failed: both Playwright and urllib returned no content"})
            return
        cache[cache_key] = {"ts": now, "url": query, "content": text}
        self._save_web_cache(cache)
        self._send_json(200, {"ok": True, "cached": False, "url": query, "content": text})

    def _web_fetch_playwright(self, url: str) -> "Optional[str]":
        """Fetch a URL using the Playwright helper for JS-rendered pages. Returns text or None."""
        helper = Path(__file__).with_name("web_fetch_playwright.mjs")
        if not helper.exists() or not shutil.which("node"):
            return None
        request = json.dumps({"url": url, "timeout": 22000}, ensure_ascii=True)
        try:
            run = subprocess.run(
                ["node", str(helper), request],
                cwd=str(Path(__file__).resolve().parent.parent),
                env=dict(os.environ),
                capture_output=True,
                text=True,
                timeout=50,
            )
        except (subprocess.TimeoutExpired, Exception):
            return None
        stdout = (run.stdout or "").strip()
        try:
            data = json.loads(stdout) if stdout else {}
        except Exception:
            return None
        content = data.get("content", "")
        if not data.get("ok") or not content or len(content.strip()) < 100:
            return None
        return content

    def _web_fetch_urllib(self, url: str) -> "Optional[str]":
        """Fallback plain HTTP fetch for simple non-JS pages. Returns text or None."""
        try:
            import urllib.request as _ur
            req = _ur.Request(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/124.0 Safari/537.36",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.5",
                },
            )
            with _ur.urlopen(req, timeout=20) as resp:
                raw_page = resp.read(2_000_000)
            text = raw_page.decode("utf-8", errors="ignore")
            text = re.sub(r"(?is)<(script|style|noscript).*?</\1>", " ", text)
            text = re.sub(r"(?s)<[^>]+>", " ", text)
            text = re.sub(r"\s+", " ", text).strip()[:20000]
            return text if len(text) >= 100 else None
        except Exception:
            return None

    def _records_search(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length > MAX_JSON_BODY_BYTES:
                self._send_json(413, {"ok": False, "error": "records search payload too large"})
                return
            raw = self.rfile.read(length) if length > 0 else b"{}"
            payload = json.loads(raw.decode("utf-8"))
            subject = str(payload.get("subject") or payload.get("name") or payload.get("query") or "").strip()
            locations = payload.get("locations", [])
            if not isinstance(locations, list):
                locations = [str(locations)]
            locations = [str(x).strip() for x in locations if str(x).strip()]
        except Exception:
            self._send_json(400, {"ok": False, "error": "invalid records search payload"})
            return
        if not subject:
            self._send_json(400, {"ok": False, "error": "subject is required"})
            return
        helper = Path(__file__).with_name("records_search_playwright.mjs")
        if not helper.exists():
            self._send_json(500, {"ok": False, "error": "records search helper is missing"})
            return
        if not shutil.which("node"):
            self._send_json(500, {"ok": False, "error": "Node.js is required for Playwright records search"})
            return
        request = json.dumps({"subject": subject, "locations": locations}, ensure_ascii=True)
        env = dict(os.environ)
        try:
            run = subprocess.run(
                ["node", str(helper), request],
                cwd=str(Path(__file__).resolve().parent.parent),
                env=env,
                capture_output=True,
                text=True,
                timeout=150,
            )
        except subprocess.TimeoutExpired:
            self._send_json(504, {"ok": False, "error": "records search timed out"})
            return
        except Exception as e:
            self._send_json(500, {"ok": False, "error": f"records search failed: {e}"})
            return
        stdout = (run.stdout or "").strip()
        try:
            data = json.loads(stdout) if stdout else {}
        except Exception:
            data = {"ok": False, "error": "records search returned invalid json"}
        if run.returncode != 0 or not data.get("ok"):
            err = data.get("error") or (run.stderr or "records search failed").strip()
            self._send_json(502, {"ok": False, "error": err})
            return
        # The helper already filters for subject + location corroboration; keep only compact fields.
        matches = data.get("matches", [])
        if not isinstance(matches, list):
            matches = []
        data["matches"] = matches[:20]
        self._send_json(200, data)

    def _task_execute(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length) if length > 0 else b"{}"
            payload = json.loads(raw.decode("utf-8"))
        except Exception:
            self._send_json(400, {"ok": False, "error": "invalid json payload"})
            return
        linked = self._load_linked_dir()
        try:
            out = execute_contract(payload, linked_root=linked)
            self._send_json(200, out)
        except ContractError as e:
            self._send_json(400, {"ok": False, "error": str(e)})
        except Exception as e:
            self._send_json(500, {"ok": False, "error": f"task execution failed: {e}"})

    def _autogen_build(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length) if length > 0 else b"{}"
            payload = json.loads(raw.decode("utf-8"))
        except Exception:
            self._send_json(400, {"ok": False, "error": "invalid json payload"})
            return
        description = str(payload.get("description", "")).strip()
        mode = str(payload.get("mode", "both")).strip().lower()
        models = payload.get("models", [])
        if not isinstance(models, list):
            models = []
        ollama_base = str(payload.get("ollama_base", "http://127.0.0.1:11434")).strip()
        planner_model = str(payload.get("planner_model", "")).strip()
        try:
            out = build_autogen_plan(
                description=description,
                mode=mode,
                models=[str(m) for m in models],
                ollama_base=ollama_base,
                planner_model=planner_model,
            )
            self._send_json(200, out)
        except AutoGenError as e:
            self._send_json(400, {"ok": False, "error": str(e)})
        except Exception as e:
            self._send_json(500, {"ok": False, "error": f"autogen failed: {e}"})

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
            # Quarantine the corrupted file instead of hard-failing forever -
            # a single bad write (crash mid-save, full disk) should not
            # permanently lock the panel that reads this store key.
            try:
                quarantine = path.with_suffix(f".corrupt-{int(time.time())}.json")
                path.replace(quarantine)
            except Exception:
                pass
            self._send_json(200, {"ok": True, "data": [], "recovered_from_corruption": True})
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
        if seg == ["favicon.ico"]:
            self.send_response(204)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        if len(seg) == 4 and seg[0] == "api" and seg[1] == "store":
            self._store_get(seg[2], seg[3])
            return
        if seg == ["api", "files", "list"]:
            self._files_list()
            return
        if seg == ["api", "files", "linked-dir"]:
            self._files_linked_dir_get()
            return
        if seg == ["api", "vectors"]:
            self._vector_get()
            return
        if seg == ["api", "metrics"]:
            self._metrics()
            return
        super().do_GET()

    # ── Apple SMC reader (Apple Silicon GPU cluster temps without sudo) ──────────
    @staticmethod
    def _read_apple_smc_gpu_temp():
        """
        Read GPU cluster temperature from Apple SMC via IOKit on macOS.
        Works on Apple Silicon (M1/M2/M3/M4) without sudo or extra tools.
        Returns the highest GPU cluster temp in °C, or None on failure.
        """
        import ctypes, struct, platform
        if platform.system() != "Darwin":
            return None
        try:
            # Apple Silicon GPU die/cluster SMC keys.
            # M1: Tg05, Tg0D  |  M2/M3/M4: Tg0e, Tg0f, Tg0m, Tg0n, Tg0q, Tg0r
            GPU_KEYS = ("Tg05", "Tg0D", "Tg0e", "Tg0f", "Tg0m", "Tg0n", "Tg0q", "Tg0r")

            iokit = ctypes.CDLL(
                "/System/Library/Frameworks/IOKit.framework/Versions/A/IOKit",
                use_errno=True,
            )
            libsys = ctypes.CDLL("/usr/lib/libSystem.B.dylib", use_errno=True)

            class _SMCVersion(ctypes.Structure):
                _fields_ = [
                    ("major",    ctypes.c_uint8),
                    ("minor",    ctypes.c_uint8),
                    ("build",    ctypes.c_uint8),
                    ("reserved", ctypes.c_uint8 * 1),
                    ("release",  ctypes.c_uint16),
                ]

            class _SMCPLimitData(ctypes.Structure):
                _fields_ = [
                    ("version",   ctypes.c_uint16),
                    ("length",    ctypes.c_uint16),
                    ("cpuPLimit", ctypes.c_uint32),
                    ("gpuPLimit", ctypes.c_uint32),
                    ("memPLimit", ctypes.c_uint32),
                ]

            class _SMCKeyInfoData(ctypes.Structure):
                _fields_ = [
                    ("dataSize",       ctypes.c_uint32),
                    ("dataType",       ctypes.c_uint32),
                    ("dataAttributes", ctypes.c_uint8),
                ]

            class _SMCParamStruct(ctypes.Structure):
                _fields_ = [
                    ("key",         ctypes.c_uint32),
                    ("vers",        _SMCVersion),
                    ("pLimitData",  _SMCPLimitData),
                    ("keyInfo",     _SMCKeyInfoData),
                    ("result",      ctypes.c_uint8),
                    ("status",      ctypes.c_uint8),
                    ("data8",       ctypes.c_uint8),
                    ("padding",     ctypes.c_uint8),
                    ("data32",      ctypes.c_uint32),
                    ("bytes",       ctypes.c_uint8 * 32),
                ]

            iokit.IOServiceGetMatchingService.restype  = ctypes.c_uint32
            iokit.IOServiceGetMatchingService.argtypes = [ctypes.c_uint32, ctypes.c_void_p]
            iokit.IOServiceMatching.restype  = ctypes.c_void_p
            iokit.IOServiceMatching.argtypes = [ctypes.c_char_p]
            iokit.IOServiceOpen.restype  = ctypes.c_int
            iokit.IOServiceOpen.argtypes = [
                ctypes.c_uint32, ctypes.c_uint32, ctypes.c_uint32,
                ctypes.POINTER(ctypes.c_uint32),
            ]
            iokit.IOConnectCallStructMethod.restype  = ctypes.c_int
            iokit.IOConnectCallStructMethod.argtypes = [
                ctypes.c_uint32, ctypes.c_uint32,
                ctypes.c_void_p, ctypes.c_size_t,
                ctypes.c_void_p, ctypes.POINTER(ctypes.c_size_t),
            ]
            iokit.IOServiceClose.restype  = ctypes.c_int
            iokit.IOServiceClose.argtypes = [ctypes.c_uint32]
            iokit.IOObjectRelease.restype  = ctypes.c_int
            iokit.IOObjectRelease.argtypes = [ctypes.c_uint32]

            kIOMasterPortDefault = 0
            KERNEL_INDEX_SMC     = 2
            SMC_CMD_READ_KEYINFO = 9
            SMC_CMD_READ_BYTES   = 5

            service = iokit.IOServiceGetMatchingService(
                kIOMasterPortDefault,
                iokit.IOServiceMatching(b"AppleSMC"),
            )
            if not service:
                return None

            conn = ctypes.c_uint32(0)
            # mach_task_self_ is a global variable in libSystem, not a function
            task = ctypes.c_uint32.in_dll(libsys, "mach_task_self_").value
            ret  = iokit.IOServiceOpen(service, task, KERNEL_INDEX_SMC, ctypes.byref(conn))
            iokit.IOObjectRelease(service)
            if ret != 0:
                return None

            def _key_u32(k):
                return struct.unpack(">I", k.encode("ascii"))[0]

            def _read_key(key_str):
                inp  = _SMCParamStruct(); out = _SMCParamStruct()
                sz   = ctypes.c_size_t(ctypes.sizeof(_SMCParamStruct))
                inp.key   = _key_u32(key_str)
                inp.data8 = SMC_CMD_READ_KEYINFO
                if iokit.IOConnectCallStructMethod(
                    conn, KERNEL_INDEX_SMC,
                    ctypes.byref(inp), ctypes.sizeof(inp),
                    ctypes.byref(out),  ctypes.byref(sz),
                ) != 0:
                    return None
                data_size = out.keyInfo.dataSize
                data_type = out.keyInfo.dataType
                inp2 = _SMCParamStruct(); out2 = _SMCParamStruct()
                sz2  = ctypes.c_size_t(ctypes.sizeof(_SMCParamStruct))
                inp2.key              = _key_u32(key_str)
                inp2.keyInfo.dataSize = data_size
                inp2.data8            = SMC_CMD_READ_BYTES
                if iokit.IOConnectCallStructMethod(
                    conn, KERNEL_INDEX_SMC,
                    ctypes.byref(inp2), ctypes.sizeof(inp2),
                    ctypes.byref(out2),  ctypes.byref(sz2),
                ) != 0:
                    return None
                raw = bytes(out2.bytes[:data_size])
                # strip spaces and nulls — type tags are 4-char padded e.g. 'flt '
                typ = struct.pack(">I", data_type).decode("ascii", errors="replace").strip()
                if   typ == "sp78" and data_size >= 2:
                    val = struct.unpack(">h", raw[:2])[0] / 256.0
                elif typ == "flt"  and data_size >= 4:
                    val = struct.unpack("<f", raw[:4])[0]
                elif typ == "fpe2" and data_size >= 2:
                    val = struct.unpack(">H", raw[:2])[0] / 4.0
                else:
                    return None
                return val if 0 < val < 150 else None

            temps = [t for k in GPU_KEYS if (t := _read_key(k)) is not None]
            iokit.IOServiceClose(conn)
            return max(temps) if temps else None
        except Exception:
            return None

    def _metrics(self):
        """GET /api/metrics — lightweight system metrics (GPU/CPU temp, util)."""
        metrics = {"gpu_temp": None, "cpu_temp": None, "gpu_util": None}
        # NVIDIA GPU via nvidia-smi
        if shutil.which("nvidia-smi"):
            try:
                r = subprocess.run(
                    ["nvidia-smi", "--query-gpu=temperature.gpu,utilization.gpu",
                     "--format=csv,noheader,nounits"],
                    capture_output=True, text=True, timeout=2
                )
                if r.returncode == 0:
                    parts = r.stdout.strip().split(",")
                    if len(parts) >= 2:
                        metrics["gpu_temp"] = float(parts[0].strip())
                        metrics["gpu_util"] = float(parts[1].strip())
            except Exception:
                pass
        # macOS Apple Silicon: read GPU cluster temps directly from SMC via IOKit
        if metrics["gpu_temp"] is None:
            t = self._read_apple_smc_gpu_temp()
            if t is not None:
                metrics["gpu_temp"] = t
        # macOS: osx-cpu-temp (brew install osx-cpu-temp) — Intel Mac fallback
        if metrics["gpu_temp"] is None and shutil.which("osx-cpu-temp"):
            try:
                r = subprocess.run(["osx-cpu-temp", "-g"], capture_output=True, text=True, timeout=2)
                if r.returncode == 0:
                    import re as _re
                    m = _re.search(r"([\d.]+)\s*°?C", r.stdout)
                    if m:
                        metrics["gpu_temp"] = float(m.group(1))
            except Exception:
                pass
        # Linux: read from /sys/class/thermal
        if metrics["gpu_temp"] is None:
            try:
                import glob as _glob
                for tp in _glob.glob("/sys/class/thermal/thermal_zone*/temp"):
                    raw = Path(tp).read_text().strip()
                    val = int(raw) / 1000.0
                    if 20 < val < 120:
                        metrics["cpu_temp"] = val
                        break
            except Exception:
                pass
        # psutil sensors fallback
        if metrics["gpu_temp"] is None and metrics["cpu_temp"] is None:
            try:
                import psutil as _ps
                temps = _ps.sensors_temperatures()
                for k in ("coretemp", "cpu_thermal", "acpitz", "k10temp", "gpu_thermal"):
                    if k in temps and temps[k]:
                        val = temps[k][0].current
                        if k.startswith("gpu"):
                            metrics["gpu_temp"] = val
                        else:
                            metrics["cpu_temp"] = val
                        break
            except Exception:
                pass
        self._send_json(200, {"ok": True, "metrics": metrics})

    def do_POST(self):
        parts = urllib.parse.urlparse(self.path)
        seg = [s for s in parts.path.split("/") if s]
        if len(seg) == 4 and seg[0] == "api" and seg[1] == "store":
            self._store_set(seg[2], seg[3])
            return
        if seg == ["api", "files", "upload"]:
            self._files_upload()
            return
        if seg == ["api", "files", "link-dir"]:
            self._files_link_dir()
            return
        if seg == ["api", "files", "unlink-dir"]:
            self._files_unlink_dir()
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
        if seg == ["api", "vectors", "save"]:
            self._vector_save_doc()
            return
        if seg == ["api", "vectors", "delete"]:
            self._vector_delete_doc()
            return
        if seg == ["api", "vectors", "clear"]:
            self._vector_clear()
            return
        if seg == ["api", "vectors", "import"]:
            self._vector_import()
            return
        if seg == ["api", "web", "fetch"]:
            self._web_fetch()
            return
        if seg == ["api", "web", "records-search"]:
            self._records_search()
            return
        if seg == ["api", "task", "execute"]:
            self._task_execute()
            return
        if seg == ["api", "autogen", "build"]:
            self._autogen_build()
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
        try:
            super().end_headers()
        except self._CLIENT_DISCONNECT_ERRORS:
            # Client closed the socket before headers were flushed.
            return

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

    server = http.server.ThreadingHTTPServer((host, port), SilentHandler)
    server.daemon_threads = True
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

    # Suppress the spurious KeyboardInterrupt traceback Python 3.12+ emits
    # from threading._shutdown when Ctrl+C interrupts daemon threads.
    def _quiet_thread_excepthook(args):
        if args.exc_type is KeyboardInterrupt:
            return
        threading.__excepthook__(args)  # type: ignore[attr-defined]
    threading.excepthook = _quiet_thread_excepthook

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print(f"\n\n  {AM}◼{R} Server stopped. Goodbye.\n")
        server.server_close()
        os._exit(0)

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
