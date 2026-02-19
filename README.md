# ● OCI Ollama Command Interface V2

**Hardened. Local. Secure.**  
A local-only Ollama GUI launcher with strict endpoint validation, CSP enforcement, and intelligent file attachment context injection.

---

## Overview

OCI is a lightweight, secure Ollama GUI launcher that runs entirely on `localhost`. It provides single-page interface with intelligent file context injection, CSP hardening, and zero external dependencies.

**What's Included**:
- `files/launch_ollama_gui.py` — Local HTTP server
- `files/ollama_gui.html` — Single-page UI
- `quick-start.sh` — Setup & launch
- `scripts/security-audit.sh` — Security verification

---

## Quick Start

### Prerequisites

1. **Python 3** (for launcher)
2. **Ollama** (installed and running locally)
3. **Node.js + npm** (for task scripting)

### Setup and Launch

#### 1. Validate environment (first time)
```bash
npm run validate
```

#### 2. Start Ollama daemon
```bash
ollama serve
```

#### 3. Launch the GUI (stealth mode — no browser auto-open)
```bash
npm start
```

#### 4. Open in browser
Navigate to: `http://127.0.0.1:8765/ollama_gui.html`

### Optional: Auto-open browser
```bash
npm run start:browser
```

---

## Interface Preview

![OCI Ollama Command Interface GUI](files/Screenshot%202026-02-18%20at%209.14.05%20PM.png)

---

## Security & Hardening

The application is hardened to ensure your data never leaves your machine:

### Endpoint Restrictions
- **Inference endpoint allowlist**: `127.0.0.1`, `localhost`, `::1` only
- Remote endpoint attempts are blocked at runtime
- GUI logic validates all endpoints before connection

### Headers & Policy
- **CSP** enforced in HTML and HTTP responses
- No external font or resource calls
- Referrer policy disabled

### Applied Response Headers
```
X-Frame-Options: DENY
X-Content-Type-Options: nosniff  
Referrer-Policy: no-referrer
Permissions-Policy: (restrictive)
```

### Verify Security Controls
```bash
npm run audit:security
```

---

## Features

### File Attachments & Context Injection

Files uploaded through the GUI file panel are **active by default** and automatically injected into model prompts across all execution modes:

- **Single chat messages** — `send()`
- **Parallel model runs** — Execute same prompt on multiple models
- **Agent execution** — AI agents have access to attached file content
- **Pipeline steps** — Multi-step workflows use file context

> **Note**: Only files uploaded in the GUI file panel are included. IDE/chat attachments must be explicitly added through the GUI.

### Model Modes

- **Single Send** — Standard chat interface
- **Parallel Execution** — Run same prompt against multiple models simultaneously
- **Agent Mode** — Task-driven execution with context
- **Pipeline Mode** — Multi-step workflows with file attachments

---

## NPM Commands

| Command | Purpose |
|---------|---------|
| `npm run validate` | Check environment prerequisites |
| `npm start` | Launch GUI (stealth mode) |
| `npm run start:browser` | Launch with auto-open browser |
| `npm run audit:security` | Verify security controls |

---

## Project Structure

```
ollama-gui/
├── README.md                      # Documentation
├── package.json                   # NPM config
├── package-lock.json              # Dependencies lock
├── quick-start.sh                 # Launch script
├── files/
│   ├── launch_ollama_gui.py       # HTTP server
│   └── ollama_gui.html            # UI application
└── scripts/
    └── security-audit.sh          # Security checks
```

---

## How It Works

1. **Launch Phase**
   - `quick-start.sh` validates prerequisites (Python, Ollama, npm)
   - `launch_ollama_gui.py` starts a local HTTP server on `127.0.0.1:8765`
   - Server applies strict CSP and security headers

2. **Runtime Phase**
   - User accesses `http://127.0.0.1:8765/ollama_gui.html` in browser
   - GUI enforces localhost-only endpoint policy
   - Attached files are injected into prompts in real-time

3. **Model Interaction**
   - All inference requests route to local Ollama instance
   - File attachments are included in context per mode
   - Responses streamed back to browser UI

---

## Security Posture Summary

✓ **Localhost-only** — No remote connections allowed  
✓ **No external dependencies** — Zero cloud calls  
✓ **Content Security Policy** — Strict CSP headers enforced  
✓ **Hardened headers** — Frame options, MIME type protection, referrer policies  
✓ **File context injection** — Automatic for local analysis flows  

---

## Key Points

- **Local-only** — All operations restricted to your machine. Network access blocked.
- **Active attachments** — Files are enabled by default. Remove from panel to exclude from context.
- **Verified architecture** — No historical `src/` or multi-module remnants.

---

## Troubleshooting

### GUI won't load
- Verify Ollama daemon is running: `ollama serve`
- Check Python is installed: `python3 --version`
- Verify port 8765 is not in use

### Security audit fails
```bash
npm run audit:security
```
Review output and ensure all local-only restrictions are in place.

### Files not appearing in context
- Verify files are uploaded via GUI file panel
- Confirm file panel shows them as "active"
- IDE attachments must be manually added to GUI

---

**Status**: Verified February 19, 2026
