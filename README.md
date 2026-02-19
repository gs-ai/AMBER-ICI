<p align="center">
  <img alt="OCI | Ollama Command Interface" src="https://img.shields.io/badge/OCI%20%7C%20Ollama%20Command%20Interface-C76500?style=for-the-badge&labelColor=C76500&color=A84D00" />
</p>

<p align="center">
  <img alt="LOCAL CONTROL PLANE" src="https://img.shields.io/badge/LOCAL%20CONTROL%20PLANE-FFB347?style=flat-square&labelColor=FFB347&color=FFB347" />
  <img alt="CHAT" src="https://img.shields.io/badge/CHAT-E58A00?style=flat-square&labelColor=E58A00&color=E58A00" />
  <img alt="PARALLEL" src="https://img.shields.io/badge/PARALLEL-D97B00?style=flat-square&labelColor=D97B00&color=D97B00" />
  <img alt="AGENTS" src="https://img.shields.io/badge/AGENTS-C96A00?style=flat-square&labelColor=C96A00&color=C96A00" />
  <img alt="CHAINS" src="https://img.shields.io/badge/CHAINS-B85A00?style=flat-square&labelColor=B85A00&color=B85A00" />
  <img alt="GRAPH EXPORT" src="https://img.shields.io/badge/GRAPH%20EXPORT-A84D00?style=flat-square&labelColor=A84D00&color=A84D00" />
</p>

<p align="center">
  Local-only Ollama GUI. No remote endpoints.
</p>

## What This Is

OCI is a single-page local interface for running Ollama workflows with:

- Chat
- Parallel model runs
- Agents
- Chains (pipeline steps)
- Graph visualization
- Full-session export

All runtime traffic is constrained to localhost endpoints.

## Start The Program

1. Start Ollama:
```bash
ollama serve
```
2. Start OCI:
```bash
npm start
```
3. Open in browser:
`http://127.0.0.1:8765/ollama_gui.html`

Optional auto-open:
```bash
npm run start:browser
```

## GUI Example

<p align="center">
  <img src="files/img2377dag8adw7g.png" alt="OCI GUI example" width="1200" />
</p>

## How To Use Files

1. Open the `FILES` tab in the left panel.
2. Drag-and-drop or choose files (`.txt`, `.md`, `.pdf`, `.docx`).
3. Keep files marked `ACTIVE` to inject them into prompts.
4. Disable a file to exclude it from inference context.
5. Remove files from the list to fully drop them from session context.

Behavior:
- Active files are prepended into prompt context in chat, parallel runs, agents, and pipeline steps.

## How To Use Agents

1. Open `AGENTS` in the left panel.
2. Click `+ NEW AGENT`.
3. Set:
   - Agent name
   - Model
   - System prompt
   - Execution mode (`SEQUENTIAL` or `PARALLEL`)
   - Feed target
4. Save the agent.
5. Run one agent with `RUN`, or run all with `RUN ALL`.

Behavior:
- Agent outputs are written into the main session transcript.
- Parallel agents execute concurrently when `RUN ALL` is used.

## How To Use Chains (Pipeline)

1. Open `CHAIN` in the left panel.
2. Click `+ ADD STEP`.
3. For each step set:
   - Model
   - Optional system prompt
   - Template (`{{input}}` supported)
4. Add multiple steps in order.
5. Enter seed input in the main prompt box.
6. Click `RUN PIPE`.

Behavior:
- Each step output becomes next step input.
- Step messages are appended to the main transcript and reflected in graph extraction.

## Export Behavior (Confirmed)

Export is implemented in `files/ollama_gui.html` and includes:

- Full transcript from all rendered session messages (chat + parallel + agent + pipeline)
- Explicit `PARALLEL CONVERSATIONS` section
- Agent configuration snapshot
- Pipeline configuration snapshot
- Graph nodes/edges snapshot
- File snapshot

Code references:
- `files/ollama_gui.html:1173` (`collectTranscript()`)
- `files/ollama_gui.html:1189` (`expChat()`)
- `files/ollama_gui.html:1237` (`PARALLEL CONVERSATIONS` section)

## Commands

| Command | Purpose |
|---------|---------|
| `npm start` | Start OCI without opening browser |
| `npm run start:browser` | Start OCI and open browser |

## Project Layout

```text
.
├── README.md
├── package.json
└── files/
    ├── launch_ollama_gui.py
    ├── ollama_gui.html
    └── img2377dag8adw7g.png
```
