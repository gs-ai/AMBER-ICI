<p align="center">
  <img src="image/README/06b51b0b-382c-46e8-9942-6163001684c0.png" alt="AMBER ICI interface banner" width="1200" />
</p>

# AMBER ICI

AMBER ICI (AMBER Investigative Command Interface) is a local-first Ollama command interface for investigative and analytical workflows.

It provides:
- Analyst Console for direct model interaction
- Parallel model execution
- Agent orchestration with loops
- Chain/Pipeline execution with loops
- Integrated local Archive (semantic vector index/search)
- Graph correlation view
- Local file ingestion with PDF/DOCX/TXT/MD extraction
- OCR fallback for PDFs (when OCR dependencies are installed)
- Local runtime telemetry (token rate, session stats, GPU/VRAM)

All inference is intended to run locally against Ollama (`127.0.0.1`/`localhost`).

## Repository About (GitHub)

Industrial-grade local Ollama command center with multi-model orchestration, live token streaming, graph-based output correlation, investigative file ingestion, agent pipelines, and GPU telemetry. Built for local-first analysis, OSINT workflows, transcript ingestion, OCR extraction, and model chaining.

## v3 Update Highlights

`v3` introduces the expanded operational workflow and storage/runtime hardening:

- UI identity updated to `v3`.
- Integrated `ARCHIVE` mode in the main UI for semantic indexing/search.
- Added standalone tools:
  - `amber_timeline.html`
  - `amber_vectorstore.html`
- Disk-backed persistence moved to `state/*.json` (away from browser-only state).
- Disk-backed uploads under `uploads/blobs`, `uploads/texts`, and `uploads/manifest.json`.
- Agent and Chain/Pipeline enhancements:
  - edit support
  - drag/drop reordering
  - loop execution controls
- Unified STOP handling across Analyst, Parallel, Agents, and Pipeline runs.
- CTX now applied consistently across Analyst, Parallel, Agents, and Pipeline inference calls.
- Automatic file-context budgeting and relevance trimming for large active file context.
- Scratchpad injection cap for `{{scratchpad}}` templates.
- Session/token telemetry now updates during Agent and Pipeline execution (not only Analyst).
- Graph enhancements for inferred property/similarity-based node connections.
- PDF ingestion now includes OCR fallback (`ocrmypdf` + `tesseract`) when available.

<p align="center">
  <img src="image/README/lksjofuh3297afw9e7ywhf.png" alt="AMBER ICI analyst console UI" width="1200" />
</p>

## Core Design

- Local-only launcher and CSP policy (no external domains configured)
- Disk-backed app state (`state/*.json`) instead of browser-only persistence
- Disk-backed uploads (`uploads/blobs`, `uploads/texts`, `uploads/manifest.json`)
- Unified STOP control for active runs
- CTX-driven prompt budget applied across Analyst, Parallel, Agents, and Pipeline

## Requirements

- Python 3.10+
- Ollama installed and running locally
- Node/npm (only used to run convenience scripts)
- Required embed model for archive/index features:
  - `mxbai-embed-large:latest`

OCR support for scanned/visual PDFs:
- `ocrmypdf`
- `tesseract`

If OCR tools are unavailable, AMBER still runs; PDF extraction falls back to basic text extraction.

## Install And Setup

### 1. Clone and enter project

```bash
git clone https://github.com/gs-ai/AMBER-ICI.git
cd AMBER-ICI
```

### 2. Start Ollama

```bash
ollama serve
```

### 3. Pull required models

Required for Archive indexing/search:

```bash
ollama pull mxbai-embed-large:latest
```

Pull any generation models you plan to use (examples):

```bash
ollama pull deepseek-r1:7b
ollama pull qwen2.5-coder:7b
ollama pull dolphin-llama3:latest
```

### 4. (Recommended) Install OCR tools for PDF ingestion

macOS (Homebrew):

```bash
brew install ocrmypdf tesseract
```

Ubuntu/Debian:

```bash
sudo apt-get update
sudo apt-get install -y ocrmypdf tesseract-ocr
```

Windows:
- Install `Tesseract OCR`
- Install `OCRmyPDF`
- Ensure both are available in your `PATH`

### 5. Launch AMBER ICI

Browser auto-open:

```bash
npm run start:browser
```

No auto-open:

```bash
npm start
```

Direct Python launch (same backend):

```bash
python3 files/launch_amber_ici_gui.py --host 127.0.0.1 --port 8765
```

Open:

- `http://127.0.0.1:8765/amber_ui.html`

## Launcher Options

```bash
python3 files/launch_amber_ici_gui.py --help
```

Supported flags:
- `--host` (default `127.0.0.1`)
- `--port` (default `8765`)
- `--no-browser`
- `--gui PATH`

## First-Run Workflow

1. Confirm endpoint (top-right): `http://127.0.0.1:11434`
2. Click `PING`
3. Select one model in `MODELS`
4. Use `ANALYST CONSOLE` to send prompt
5. Upload files in `FILES` (optional)
6. Mark uploaded files active so they become context for runs

## Workspaces And How They Run

### Analyst Console

Use for direct single-model interaction.

- `SEND` activates when exactly one active model context is selected
- Supports system prompt, stream toggle, JSON output mode, CTX setting, seed
- `STOP` / `ESC` aborts active run

### Parallel

Run the same prompt across checked models.

- Select multiple models via checkboxes
- Click `RUN CHECKED PARALLEL`
- Per-model outputs stream independently

### Agents

Card-based orchestration with execution modes.

- Add/Edit/Delete agents
- Reorder agent cards by drag-and-drop
- Set loop count (`LOOPS`)
- `RUN` under Agents executes the configured agent chain

### Chain / Pipeline

Ordered step execution using templates.

- Add/Edit/Delete steps
- Template supports `{{input}}` and `{{scratchpad}}`
- Reorder steps by drag-and-drop
- Set loop count (`LOOPS`)
- `RUN CHAIN` executes current steps

### Archive (Integrated)

Local semantic archive in the main UI.

- Queue active files
- Index queued files with `mxbai-embed-large:latest`
- Search by semantic similarity
- Export/import archive JSON
- Add last assistant output to archive directly

## File Ingestion

Accepted types:
- `.txt`, `.md`, `.pdf`, `.docx`

Limits:
- Max upload size: `32 MB` per file

Storage:
- Raw bytes: `uploads/blobs/`
- Extracted text: `uploads/texts/`
- File manifest: `uploads/manifest.json`

PDF extraction behavior:
- Basic text extraction always attempted
- OCR fallback attempted when `ocrmypdf` is available
- Better of basic vs OCR text is saved as extracted text

## Context Budgeting (Current Runtime Behavior)

AMBER applies context controls automatically:

- CTX applies to Analyst, Parallel, Agents, and Pipeline requests
- Active file context budget is capped to approximately:
  - `maxChars = CTX * 3`
- If active file context exceeds budget:
  - it is trimmed using simple relevance scoring (keyword overlap)
- `{{scratchpad}}` injection is tail-capped:
  - min ~8k chars, max ~20k chars
  - additionally bounded by file-context budget

This reduces prompt overflow and keeps runs stable as file volume increases.

## Session Stats And Telemetry

Right panel session stats update during:
- Analyst runs
- Parallel runs
- Agent runs
- Pipeline runs

Tracked fields:
- Turns
- Tok In
- Tok Out
- Peak T/S
- Avg T/S
- Live token rate sparkline

## Persistence Model

Runtime state is persisted under `state/`:

- `state/agents_state.json`
- `state/pipeline_state.json`
- `state/agent_sets.json`
- `state/chain_sets.json`
- `state/vector_store.json`
- `state/timeline_state.json`

Legacy store routes are still accepted and mapped to `state/` for compatibility.

## Standalone Utilities

In addition to integrated Archive mode, standalone pages are available:

- Timeline UI: `http://127.0.0.1:8765/amber_timeline.html`
- Vectorstore UI: `http://127.0.0.1:8765/amber_vectorstore.html`

These also persist via local API-backed state.

## Security Posture

- Launcher binds to localhost by default (`127.0.0.1`)
- CSP `connect-src` restricted to localhost addresses
- Referrer/permissions hardened in launcher headers
- No cloud endpoint is configured in this repo by default

## Data Hygiene / Cleanup

Remove runtime state:

```bash
rm -f state/*.json
```

Remove uploaded source and extracted text:

```bash
rm -rf uploads/blobs uploads/texts
rm -f uploads/manifest.json
```

## Troubleshooting

### Archive indexing fails with HTTP 500

Check:
- Embed model present: `ollama pull mxbai-embed-large:latest`
- Ollama running and reachable at `127.0.0.1:11434`
- PDF is text-extractable or OCR dependencies are installed

### PDF extracted text is poor

- Install OCR dependencies (`ocrmypdf`, `tesseract`)
- Re-upload PDF so extraction re-runs with OCR path
- Inspect saved text in `uploads/texts/<FILE_ID>.txt`

### SEND button disabled

`SEND` is enabled only when single-model send conditions are met.
Use:
- One active model for Analyst send
- Parallel button when running checked multi-model mode

### Port already in use

Use another port:

```bash
python3 files/launch_amber_ici_gui.py --host 127.0.0.1 --port 8877
```

## Project Layout

```text
AMBER/
├── files/
│   ├── amber_ui.html
│   ├── amber_timeline.html
│   ├── amber_vectorstore.html
│   └── launch_amber_ici_gui.py
├── image/
│   └── README/
├── state/
│   ├── agents_state.json
│   ├── pipeline_state.json
│   ├── agent_sets.json
│   ├── chain_sets.json
│   ├── vector_store.json
│   └── timeline_state.json
├── uploads/
│   ├── blobs/
│   ├── texts/
│   └── manifest.json
├── package.json
├── README.md
└── LICENSE
```
