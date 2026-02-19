#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
GUI_FILE="$ROOT_DIR/files/ollama_gui.html"
LAUNCHER_FILE="$ROOT_DIR/files/launch_ollama_gui.py"

fail() {
  echo "FAIL: $1" >&2
  exit 1
}

echo "Running local-only security audit..."

[[ -f "$GUI_FILE" ]] || fail "Missing $GUI_FILE"
[[ -f "$LAUNCHER_FILE" ]] || fail "Missing $LAUNCHER_FILE"

grep -q "LOCAL_ONLY_HOSTS" "$GUI_FILE" || fail "GUI host allowlist is missing"
grep -q "REMOTE ENDPOINT BLOCKED" "$GUI_FILE" || fail "GUI endpoint block message missing"
grep -q "Content-Security-Policy" "$GUI_FILE" || fail "GUI CSP meta tag missing"
grep -q "Content-Security-Policy" "$LAUNCHER_FILE" || fail "Launcher CSP header missing"
grep -q "connect-src http://127.0.0.1:\\* http://localhost:\\*" "$LAUNCHER_FILE" || fail "Launcher connect-src policy is not local-only"

if grep -Eq "https://fonts.googleapis.com|https://fonts.gstatic.com" "$GUI_FILE"; then
  fail "External webfont reference found"
fi

echo "PASS: local-only controls are present."
