#!/usr/bin/env bash

# Local launcher setup for the currently delivered codebase.
# This project currently ships a local HTML GUI + Python launcher.

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

VALIDATE_ONLY=0
if [[ "${1:-}" == "--validate-only" ]]; then
  VALIDATE_ONLY=1
fi

echo "OLLAMA LOCAL GUI // QUICK START"
echo "================================"
echo

echo -e "${CYAN}Checking Python...${NC}"
if ! command -v python3 >/dev/null 2>&1; then
  echo -e "${RED}ERROR:${NC} python3 is required."
  exit 1
fi
echo -e "${GREEN}OK:${NC} $(python3 --version)"

echo -e "${CYAN}Checking required files...${NC}"
for file in files/launch_ollama_gui.py files/ollama_gui.html; do
  if [[ ! -f "$file" ]]; then
    echo -e "${RED}ERROR:${NC} Missing $file"
    exit 1
  fi
done
echo -e "${GREEN}OK:${NC} launcher and GUI files found"

echo -e "${CYAN}Checking Ollama CLI...${NC}"
if ! command -v ollama >/dev/null 2>&1; then
  echo -e "${YELLOW}WARN:${NC} ollama CLI not found."
  echo "Install Ollama first: https://ollama.com/download"
  exit 1
fi
echo -e "${GREEN}OK:${NC} ollama installed"

echo -e "${CYAN}Checking Ollama daemon...${NC}"
if curl -sf http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
  echo -e "${GREEN}OK:${NC} Ollama daemon is reachable at 127.0.0.1:11434"
else
  echo -e "${YELLOW}WARN:${NC} Ollama daemon not reachable."
  echo "Start it in another terminal:"
  echo "  ollama serve"
  exit 1
fi

echo
echo -e "${GREEN}SETUP COMPLETE${NC}"
echo "Local-only endpoint policy is enforced in the GUI."
echo

if [[ "$VALIDATE_ONLY" -eq 1 ]]; then
  echo "Validation only mode; not launching GUI."
  exit 0
fi

echo "Launching GUI on http://127.0.0.1:8765 (manual browser open)..."
exec python3 files/launch_ollama_gui.py --host 127.0.0.1 --port 8765 --no-browser
