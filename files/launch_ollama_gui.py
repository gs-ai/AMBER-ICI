#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════╗
║   OLLAMA // COMMAND INTERFACE v2 — CLI LAUNCHER      ║
║   Launches the local GUI in your default browser.    ║
║   NO cloud. NO telemetry. NO outbound requests.      ║
╚══════════════════════════════════════════════════════╝

Usage:
    python3 launch_ollama_gui.py [--port 8765] [--no-browser]

Options:
    --port        Port to serve the GUI on (default: 8765)
    --host        Host address (default: 127.0.0.1)
    --no-browser  Don't auto-open the browser
    --gui PATH    Path to ollama_gui.html (default: auto-detected)
"""

import argparse
import http.server
import os
import socket
import sys
import threading
import time
import webbrowser
from pathlib import Path

# ── ANSI colors ────────────────────────────────────────────────────────────────
R  = "\033[0m"
BO = "\033[1m"
AM = "\033[38;5;214m"  # amber
GR = "\033[38;5;83m"   # green
DM = "\033[38;5;244m"  # dim
RD = "\033[38;5;196m"  # red
CY = "\033[38;5;117m"  # cyan

def banner():
    print(f"""
{AM}{BO}
  ██████  ██      ██      █████  ███    ███  █████
 ██    ██ ██      ██     ██   ██ ████  ████ ██   ██
 ██    ██ ██      ██     ███████ ██ ████ ██ ███████
 ██    ██ ██      ██     ██   ██ ██  ██  ██ ██   ██
  ██████  ███████ ███████ ██  ██ ██      ██ ██   ██{R}
{DM}  COMMAND INTERFACE // LOCAL INFERENCE // NO TELEMETRY{R}
""")

def check_port_free(host, port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((host, port))
            return True
        except OSError:
            return False

def find_gui_file(hint=None):
    """Locate ollama_gui.html relative to this script or from a hint."""
    if hint:
        p = Path(hint)
        if p.exists():
            return p
        print(f"{RD}ERROR:{R} GUI file not found: {hint}")
        sys.exit(1)

    # Search common locations
    candidates = [
        Path(__file__).parent / "ollama_gui.html",
        Path(__file__).parent / "gui" / "ollama_gui.html",
        Path.cwd() / "ollama_gui.html",
    ]
    for c in candidates:
        if c.exists():
            return c

    print(f"{RD}ERROR:{R} Could not find ollama_gui.html")
    print(f"{DM}  Place ollama_gui.html in the same directory as this script.{R}")
    sys.exit(1)

class SilentHandler(http.server.SimpleHTTPRequestHandler):
    """Serve files silently (no request logs)."""
    def log_message(self, *_):
        pass

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
    gui_dir = gui_path.parent
    gui_file = gui_path.name

    os.chdir(gui_dir)

    if not check_port_free(host, port):
        print(f"{RD}✗{R} Port {port} is already in use. Try --port XXXX")
        sys.exit(1)

    server = http.server.HTTPServer((host, port), SilentHandler)
    url = f"http://{host}:{port}/{gui_file}"

    print(f"  {GR}●{R} Server   : {AM}{url}{R}")
    print(f"  {GR}●{R} GUI file : {DM}{gui_path}{R}")
    print(f"  {GR}●{R} Ollama   : {DM}http://127.0.0.1:11434  (localhost only){R}")
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
        description="Launch the Ollama GUI in your browser",
        add_help=True
    )
    parser.add_argument("--port", type=int, default=8765,
                        help="Port to serve on (default: 8765)")
    parser.add_argument("--host", default="127.0.0.1",
                        help="Host address (default: 127.0.0.1)")
    parser.add_argument("--no-browser", action="store_true",
                        help="Don't auto-open browser")
    parser.add_argument("--gui", default=None,
                        help="Path to ollama_gui.html")
    args = parser.parse_args()

    gui_path = find_gui_file(args.gui)

    print(f"  {AM}OLLAMA GUI LAUNCHER{R}\n")
    launch(args.host, args.port, gui_path, not args.no_browser)

if __name__ == "__main__":
    main()
