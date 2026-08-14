<p align="center">
  <img src="image/README/06b51b0b-382c-46e8-9942-6163001684c0.png" alt="AMBER ICI interface banner" width="1200" />
</p>

# AMBER ICI v5

AMBER ICI (AMBER Investigative Command Interface) is a local-first browser interface for investigative and analytical workflows powered by a local [Ollama](https://ollama.com/) server.

It includes:

- A single-model Analyst Console and multi-model Parallel execution
- A user-defined agent chain driven from the main terminal's `SEND` button
- User control over which agents run, how many, how many loops, and which local model each uses
- Local-model generation of agent configurations from a plain-language objective
- A persistent semantic Archive backed by Ollama embeddings
- Fibonacci fractal retrieval for active-file context
- File uploads, read-only linked-directory access, text extraction, and OCR
- Optional Playwright-backed web fetch and public-record search, behind a single master switch
- Standalone entity graph, timeline, and vector-store views
- Local token-rate, session, GPU/VRAM, and temperature telemetry where available

Ollama inference is restricted by the UI to loopback endpoints (`127.0.0.1`, `localhost`, or `::1`). AMBER does not include cloud inference or application telemetry, and no feature requires a login, API key, or account. The `WEB` pill is the master switch for all internet access: with it `OFF`, AMBER makes no outbound request of any kind.

## v5 Highlights

- Local case workspaces with case-bounded evidence and Archive retrieval
- Streaming SHA-256 artifact identity, ingestion provenance, duplicate detection, and source citations
- Deterministic keyword retrieval fused with existing semantic Archive results
- Explicit, bounded memory scoped to sessions, investigators, cases, agents, or reasoning tasks
- Operator-selected investigation role templates using installed local Ollama models
- Agent execution from the main terminal with per-agent models, limits, formats, handoffs, and loop controls
- Playwright WEB preflight, visible execution diagnostics, direct-fetch fallback, and one-hour local caching
- Cached hardware detection with Metal, CUDA, ROCm, unified-memory, utilization, and temperature reporting
- Coalesced streaming updates for responsive long-form output
- Bounded persisted metadata, escaped generated UI content, reproducible Node dependencies, and expanded sensitive-runtime exclusions

## Current Feature Set

### Analyst Console

- Streams a conversation with one selected Ollama model
- Supports a system prompt, JSON output mode, seed, temperature, and CTX size
- Injects active-file, optional web, and retained conversation context
- Stops active work with `STOP` or `Esc`

The console pill bar carries the execution controls:

| Pill | Values | Purpose |
|---|---|---|
| `TEMP` / `CTX` / `MEM` / `FMT` / `STREAM` / `SEED` / `SYS` | — | Analyst-mode inference settings |
| `WEB` | `OFF` (default) / `ON` | Master switch for all internet access |
| `EXEC` | `ANALYST` (default) / `AGENTS` | What `SEND` runs: the single active model, or the agent chain |
| `AGN` | `0` = all | How many agents the chain runs, taken in card order |
| `LOOPS` | `1`+ | How many times the chain repeats; mirrored with the Agents panel `LOOPS` field |

### Parallel

- Runs the same prompt against all checked models
- Streams and tracks each response independently
- Applies the same CTX and active-file controls used by the Analyst Console

### Agents — the execution chain

Agents are user-defined and are the primary execution path. There is no built-in or fixed agent list; the Agents panel starts empty and you populate it two ways:

- `+ CREATE AGENT` — define one by hand
- `GENERATE FROM PROMPT` — describe an objective and a selected local planner model writes the agent set for you

Each agent stores its own runtime configuration:

| Field | Default | Notes |
|---|---|---|
| Agent name | — | Required |
| Agent purpose | — | Injected as `[AGENT PURPOSE]` |
| Agent system prompt | — | The agent's role instruction |
| Preferred local model | — | Required; must be installed in Ollama |
| Temperature | `0.35` | Per agent, independent of the console `TEMP` pill |
| Max output tokens | `0` (auto) | `0` uses AMBER's length heuristic |
| Loops | `1` | Passes this agent makes per chain loop, each refining its own previous output |
| Output format | plain text | `JSON` sets Ollama's JSON mode and skips length expansion |
| Handoff instructions | — | Passed to the next sequential agent as `[HANDOFF FROM PREVIOUS AGENT]` |
| Execution mode | `sequential` | `sequential`, `parallel`, or `gated` |
| Output target, memory scope, role, tool access, enabled, notes | — | Under `ADVANCED` |

**Running the chain.** Set `EXEC` to `AGENTS`, type a prompt in the main terminal, and press `SEND`. AMBER reads the selected mode, the enabled agents, each agent's local model, the `AGN` count, and the `LOOPS` count, then executes: `parallel` agents concurrently, followed by `sequential` agents in card order, once per loop. Each sequential agent receives the previous agent's output as `[UPSTREAM OUTPUT]` plus that agent's handoff note. Progress and every agent's streamed output print into the main terminal, and the final answer is retained in conversation history. The Agents panel `RUN` button does the same thing using the panel's own `LOOPS` field.

In `AGENTS` mode `SEND` does not require an active model in the Models panel, because each agent carries its own. `gated` agents are excluded from the chain — run them individually with their card's `RUN` button.

**Missing models are never substituted.** Saving an agent or starting a chain with a model that Ollama does not have prints an actionable block in the terminal naming the requested model, the models actually installed, and the `ollama pull <model>` command needed, and the run does not start.

Saved agent sets can be stored and restored by name from the Agents panel.

> The earlier `PIPELINE` / `CHAIN` step-sequence mode was retired from the interface. Its engine and `state/pipeline_state.json` remain in place for backward compatibility, but it is no longer a selectable mode; agents are the execution chain.

### Archive and Memory

- Chunks and embeds queued files with `embeddinggemma:latest`
- Searches the local archive by cosine similarity
- Imports and exports archive JSON
- Adds the most recent assistant output directly to the archive
- Builds an in-browser Fibonacci fractal index for file-source retrieval
- Offers `FAST`, `HYBRID`, and `DEEP` retrieval profiles

### Case Intelligence

The Archive now includes an optional case boundary without replacing its existing all-archive workflow:

- `NEW CASE` creates local case metadata.
- `ADD ACTIVE TO CASE` records selected files as evidence, retains the existing raw upload, computes a streaming SHA-256 identity, and records ingestion provenance.
- Archive vectors indexed while a case is selected carry that case ID. Case searches fuse those semantic results with a deterministic keyword fallback when both are available.
- `REMEMBER LAST` explicitly saves the latest assistant output as labeled case memory. Model output is never silently promoted to evidence or memory.
- `ADD INVESTIGATION ROLES` adds optional Director, Researcher, Investigator, Analyst, Documenter, and Critic templates to the existing user-defined agent registry. They use the operator-selected local model and do not run automatically.

Case intelligence is stored atomically in one versioned standard-library JSON store and uses AMBER's existing Ollama client.

### Standalone Views

The header opens these tools in separate tabs:

- Entity Provenance Graph: `http://127.0.0.1:8765/amber_graph.html`
- Timeline: `http://127.0.0.1:8765/amber_timeline.html`
- Vector Store manager: `http://127.0.0.1:8765/amber_vectorstore.html`

## Requirements

Core runtime:

- Python 3.10 or newer; the launcher and core backend use only the standard library, so no `pip install` is required to run AMBER
- Ollama installed and running locally
- At least one Ollama generation model
- `embeddinggemma:latest` for Archive indexing and semantic search

Optional capabilities:

- Node.js 18+ and npm, plus the project dependencies, for JavaScript-rendered web fetches and records search
- A Playwright Chromium browser for those browser-backed features
- `ocrmypdf` and Tesseract for PDF OCR
- Tesseract for image OCR
- Pillow for converting WebP images before OCR when Tesseract cannot read them directly
- `psutil`, `nvidia-smi`, or `osx-cpu-temp` for additional system metrics; unavailable readings simply remain blank

Everything above is local. No component requires an account, API key, or cloud service.

## Install and Run

### 1. Clone the repository

```bash
git clone https://github.com/gs-ai/AMBER-ICI.git
cd AMBER-ICI
```

### 2. Start Ollama

In a separate terminal:

```bash
ollama serve
```

Pull the required embedding model and at least one generation model:

```bash
ollama pull embeddinggemma:latest
ollama pull qwen2.5-coder:7b
```

The generation model is only an example; AMBER discovers locally installed models from Ollama.

### 3. Create the Python environment

The core backend imports only the Python standard library, so a virtual environment is optional for a direct launch. Create one anyway if you want the npm scripts (which call `venv/bin/python3`) or optional Pillow support:

```bash
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
python3 -m pip install --upgrade pip
```

There is no `requirements.txt` because nothing is required. Install optional extras into that environment only if you want them:

```bash
python3 -m pip install Pillow     # optional: WebP conversion before OCR
```

Deactivate with `deactivate`. If a previous AMBER version left unused packages in `venv/` (for example `camoufox`), they are not imported by the current code and can be ignored or removed.

### 4. Launch the core application

```bash
python3 files/launch_amber_ici_gui.py
```

AMBER opens the browser automatically. To launch without opening a tab:

```bash
python3 files/launch_amber_ici_gui.py --no-browser
```

Then open `http://127.0.0.1:8765/amber_ui.html`.

### 5. Install optional browser-backed web features

Required only if you intend to turn the `WEB` pill on:

```bash
npm install                       # playwright, playwright-extra, stealth plugin
npx playwright install chromium   # the browser binary itself
```

Verify the helpers are runnable — with AMBER running, this reports the helper paths, the resolved `node` binary, and any missing package:

```bash
curl -s http://127.0.0.1:8765/api/web/status
```

AMBER uses the Node/Chromium helper for JavaScript-rendered pages, with a plain Python HTTP fetch as a fallback for direct URLs. The records-search helper requires Node.js, the npm dependencies, and Chromium; it has no plain-HTTP fallback.

### 6. Install optional OCR support

macOS with Homebrew:

```bash
brew install ocrmypdf tesseract
python3 -m pip install Pillow
```

Ubuntu/Debian:

```bash
sudo apt-get update
sudo apt-get install -y ocrmypdf tesseract-ocr
python3 -m pip install Pillow
```

Pillow is only needed for image formats that require conversion before Tesseract can process them. AMBER continues to run when any optional OCR dependency is absent.

### npm convenience scripts

The supplied npm scripts launch AMBER with `venv/bin/python3`, so create that environment first (step 3):

```bash
npm start                 # 127.0.0.1:8765, no browser tab
npm run start:browser     # same, and opens the browser
```

Direct `python3` launch is the most portable option.

### Complete setup, start to finish

```bash
git clone https://github.com/gs-ai/AMBER-ICI.git
cd AMBER-ICI
python3 -m venv venv                       # for the npm scripts
npm install                                # optional: WEB features
npx playwright install chromium            # optional: WEB features
ollama serve &                             # in its own terminal
ollama pull embeddinggemma:latest          # required for Archive
ollama pull qwen2.5-coder:7b               # any generation model
npm start                                  # → http://127.0.0.1:8765/amber_ui.html
```

## Launcher Options

```bash
python3 files/launch_amber_ici_gui.py --help
```

| Flag | Default | Purpose |
|---|---:|---|
| `--host HOST` | `127.0.0.1` | Address on which the AMBER HTTP server listens |
| `--port PORT` | `8765` | AMBER HTTP server port |
| `--no-browser` | off | Do not open the default browser |
| `--gui PATH` | auto-detected | Serve a specific GUI HTML file |
| `--version` | — | Print the AMBER ICI release version and exit |

The browser UI intentionally accepts only loopback Ollama URLs even if the AMBER server is bound to another interface.

## First-Run Workflow

1. Confirm the Ollama endpoint in the top-right is `http://127.0.0.1:11434`.
2. Click `PING` to load locally installed models.
3. Select one model in the Models panel.
4. Enter a prompt in the Analyst Console and click `SEND`.
5. Optionally upload files or link a directory, then activate files to include them in context.
6. Pull `embeddinggemma:latest` before indexing files in Archive.

To run the agent chain instead:

1. Open the `AGENTS` tab in the left panel.
2. Create an agent with `+ CREATE AGENT`, or describe an objective under `GENERATE FROM PROMPT`.
3. Set `EXEC` to `AGENTS` in the console pill bar.
4. Set `AGN` (how many agents; `0` = all) and `LOOPS` (how many passes).
5. Type the prompt in the main terminal and press `SEND`.

To let AMBER read the internet, set the `WEB` pill to `ON` first; it is `OFF` by default.

## File Ingestion

Uploads are limited to 100 MiB per file. The file picker and drag-and-drop path currently accept:

- Documents: `.txt`, `.md`, `.pdf`, `.docx`, `.rtf`
- Data/config: `.csv`, `.xlsx`, `.json`, `.yaml`, `.yml`, `.toml`, `.ini`, `.cfg`, `.conf`, `.xml`
- Source/logs: `.py`, `.js`, `.ts`, `.tsx`, `.jsx`, `.html`, `.sql`, `.sh`, `.bash`, `.zsh`, `.log`
- Images: `.png`, `.jpg`, `.jpeg`, `.bmp`, `.webp`, `.tif`, `.tiff`, `.svg`

Extraction behavior:

- Plain-text, source, configuration, CSV, and RTF files are decoded as text.
- XLSX worksheets are extracted with the Python standard library; formulas and complex formatting are not preserved.
- DOCX text is extracted from the document XML; complex layout is not preserved.
- PDF extraction first attempts embedded text and also attempts OCR when `ocrmypdf` is installed, retaining the more useful result.
- Raster images use Tesseract OCR when installed. SVG extraction reads embedded `<text>` and `<tspan>` content.

Uploaded raw bytes are stored in `uploads/blobs/`, extracted text in `uploads/texts/`, and metadata in `uploads/manifest.json`.

### Linked directories

`LINK DIRECTORY` exposes supported, non-hidden files from one local directory to AMBER. The Files panel treats linked entries as read-only, and directory listing is non-recursive. The selected path is stored in `state/linked_dir_state.json`; file content remains in its original location and is read only when requested for context or extraction.

The native folder chooser uses Python's Tkinter. If it is unavailable, the UI prompts for a path manually. Unlinking the directory removes the saved link but does not delete source files.

The backend recognizes a few additional linked-file formats (`.xls`, `.ods`, `.gif`, `.heic`, `.ico`, `.ppt`, `.pptx`, and `.zip`). Formats without a text extractor contribute a metadata label rather than decoded content. Legacy `.xls` and `.ods` extraction is best-effort and may report that extraction is unavailable.

## Context and Memory Behavior

CTX options in the UI are `2K`, `4K`, `8K`, `16K`, and `32K` and apply across Analyst, Parallel, and Agent calls.

- Before inference, `trimMsgsToCtx()` removes the oldest non-system messages until the request fits about 90% of the selected context budget, estimated at four characters per token.
- Active-file retrieval first queries the Fibonacci fractal store, when populated, and falls back to flat file-context assembly.
- Retrieval uses up to depth 4, beam width 2–4, and profile-dependent result limits.
- Active-file context is capped according to the memory profile: approximately `CTX × 2.6` characters in Fast, `CTX × 3.2` in Hybrid, and `CTX × 4.0` in Deep.
- Oversized flat context is ranked with keyword-overlap scoring before injection.
- Scratchpad injection keeps a tail of roughly 8,000–20,000 characters and is additionally bounded by the active profile's file-context budget.
- Agents with full memory receive the last six conversation messages. Local memory uses a scratchpad tail; `none` disables that recall.

These are character-based guardrails, not exact tokenizer counts.

The vector Archive is durable, but the separate Fibonacci tree is session memory. It is built for a file when that file is indexed during the current page session and is not automatically reconstructed from `state/vector_store.json` after a reload; until rebuilt, active-file context uses the flat fallback.

## Persistence

The launcher stores durable application data as JSON under `state/` using atomic temporary-file replacement. There is no active SQLite migration or database dependency.

| Path | Contents |
|---|---|
| `state/agents_state.json` | Current agents, including each agent's model, temperature, token limit, loops, format, and handoff |
| `state/agent_sets.json` | Saved agent presets |
| `state/agent_run_log.json` | Last 100 agent executions: agent, model, duration, success, and context |
| `state/pipeline_state.json` | Retired pipeline steps, retained for backward compatibility |
| `state/chain_sets.json` | Saved chain presets |
| `state/step_run_log.json`, `state/tool_call_log.json`, `state/tool_registry_state.json` | Step, tool-call, and tool-registry records |
| `state/chat_history.json` | Last 100 conversation messages; the UI replays the latest 30 |
| `state/scratch.json` | Last 20,000 scratchpad characters |
| `state/memory_profile.json` | Fast, Hybrid, or Deep retrieval selection |
| `state/vector_store.json` | Archive chunks and embeddings |
| `state/case_intelligence.json` | Case metadata, evidence contracts and provenance, bounded explicit memory, and agent trace receipts; created on the first write |
| `state/graph_state.json`, `state/timeline_state.json` | Graph and timeline data |
| `state/web_cache.json` | Direct web-fetch results with a one-hour TTL |
| `state/linked_dir_state.json` | Current linked-directory path |
| `uploads/manifest.json` | Uploaded-file metadata |

Panel layout is stored in browser `localStorage`, so it is browser-profile specific. Runtime-only selections, statistics, and the in-memory fractal tree reset on page load.

If a state JSON file cannot be decoded, the launcher quarantines it with a `.corrupt-<timestamp>.json` suffix and returns an empty value so the affected panel can recover.

## Web Access and Network Boundaries

The `WEB` pill is the master switch, and it defaults to `OFF`.

**With `WEB` off, AMBER makes no outbound request of any kind.** The gate is enforced inside the fetch functions themselves, so prompt phrasing, injected file context, and agent tool calls (`web_fetch`, `online_records_search`) are all blocked equally. If a prompt asks for a fetch while the switch is off, the terminal says so and the request is not sent rather than failing silently.

With `WEB` on, AMBER checks the helper environment first, prints the helper path it will use, and then resolves the request in this order:

1. An explicit site instruction such as “search foxnews.com for X” — fetches that site, using a known search URL when the topic is specific.
2. A specifically phrased “records search for/on [person] in [location]” request — invokes the records helper.
3. An explicit `http://`/`https://` URL or recognized bare domain in the prompt or injected file context.
4. Otherwise, the prompt text is submitted to DuckDuckGo's HTML endpoint and the results page is fetched.

Step 4 means that with `WEB` on, prompt text can reach a general search engine. Turn `WEB` off for prompts whose text should not leave the machine.

Every outcome is reported in the main terminal: the mode selected, the helper path used, the request sent, the engine that served it (`playwright`, `urllib`, or `cache`), the content size and where it was injected, or a failure block naming the missing dependency and the command that fixes it. Direct fetches are cached for one hour in `state/web_cache.json`.

Records search queries these sources and returns only matches whose page text corroborates both the subject and the requested location: `casesearch.kscourts.gov`, `doc.ks.gov/offender-search`, `kbi.ks.gov/registeredoffender`, DuckDuckGo, and Brave Search.

Network behavior is:

- Model discovery, inference, embeddings, and model status connect only to a loopback Ollama endpoint.
- The AMBER backend serves local files and API routes from the configured AMBER host/port.
- With `WEB` on, the Playwright web fetch, its Python HTTP fallback, and records search make outbound requests to user-selected, search-provider, and public-record sites. With `WEB` off, none of these run.
- `GET /api/web/status` is a local-only preflight; it inspects the filesystem and `PATH` and makes no network request.
- There is no AMBER telemetry endpoint, and no feature transmits credentials, keys, or usage data.

Fetched pages are injected into the prompt as `[WEB CONTEXT]` and therefore become part of conversation history persisted in `state/chat_history.json`; agents whose output target is the scratchpad also append to `state/scratch.json`. Live web content lands in local case state.

The launcher sends a restrictive Content Security Policy, disables framing, sets `no-referrer`, blocks sensitive browser permissions, and disables HTTP caching. The backend's `/api/task/execute` contract can list, read, write, append, or create files within the linked root when explicitly called. It rejects paths that escape that root, hidden paths, unknown tools, and overwrites that were not explicitly authorized. Link only a directory whose visible contents the local application may access and modify.

## Telemetry Panel

Session counters update during Analyst, Parallel, and Agent execution and include turns, prompt/output tokens, peak token rate, average token rate, and a live token-rate sparkline.

VRAM/model residency comes from Ollama's local `/api/ps` endpoint. Temperature/utilization readings are best-effort: NVIDIA uses `nvidia-smi`, Apple Silicon attempts direct SMC reads, Linux checks thermal zones, and optional tools provide fallbacks.

## Data Cleanup

Stop AMBER before cleanup.

Reset persisted state while preserving uploaded files:

```bash
rm -f state/*.json
```

Remove uploaded blobs, extracted text, and their manifest:

```bash
rm -rf uploads/blobs uploads/texts uploads/manifest.json
```

Linked source files are never removed by these commands. State and upload directories are recreated as needed.

## Troubleshooting

### PING fails or no models appear

- Confirm `ollama serve` is running.
- Confirm the UI endpoint is `http://127.0.0.1:11434`.
- Run `ollama list` to verify that at least one generation model is installed.

### Archive indexing fails

- Run `ollama pull embeddinggemma:latest`.
- Confirm Ollama is reachable at the endpoint shown in the UI.
- Inspect the AMBER event log for the failing embedding endpoint or input chunk.

### Browser-backed web fetch or records search fails

The terminal names the exact problem. Check the environment directly with AMBER running:

```bash
curl -s http://127.0.0.1:8765/api/web/status
```

Then install whatever it reports missing:

```bash
npm install
npx playwright install chromium
```

Direct web fetch may still succeed through its plain-HTTP fallback. Records search requires Playwright and may fail when a source changes markup, requires authentication/CAPTCHA, blocks automation, or is unavailable.

### Nothing is fetched and the terminal says `WEB IS OFF`

The `WEB` pill is `OFF`, which blocks every outbound request by design. Set it to `ON`.

### An agent will not run: `LOCAL MODEL NOT AVAILABLE`

The agent's selected model is not installed in Ollama. The terminal prints the requested model, the models you do have, and the fix:

```bash
ollama pull <model-name>
ollama list
```

AMBER never silently substitutes a different model.

### `SEND` is greyed out

In `ANALYST` mode, select exactly one model in the Models panel. In `AGENTS` mode, create at least one agent — no active model is needed there.

### PDF or image text is missing

- Install `ocrmypdf` and Tesseract.
- Install Pillow for WebP conversion if necessary.
- Re-upload the file so extraction runs again.
- Inspect the corresponding file under `uploads/texts/`.

### `npm start` cannot find Python

The npm scripts expect `venv/bin/python3`. Run `python3 -m venv venv`, or launch directly with `python3 files/launch_amber_ici_gui.py`.

### Port 8765 is already in use

```bash
python3 files/launch_amber_ici_gui.py --port 8877
```

## Project Layout

```text
AMBER-ICI/
├── files/
│   ├── amber_graph.html
│   ├── amber_timeline.html
│   ├── amber_ui.html
│   ├── amber_vectorstore.html
│   ├── amber_intelligence/       # Standard-library case/evidence/memory service
│   ├── autogen_builder.py
│   ├── constrained_executor.py
│   ├── launch_amber_ici_gui.py
│   ├── records_search_playwright.mjs
│   └── web_fetch_playwright.mjs
├── image/README/
├── state/                  # created/populated at runtime
├── uploads/                # created/populated at runtime
├── tests/                  # Case-intelligence and ICI regression tests
├── package.json
├── spec.json
├── spec.schema.json
├── README.md
└── LICENSE
```

## License

MIT. See [LICENSE](LICENSE).
