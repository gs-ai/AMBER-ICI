# OLLAMA COMMAND CENTER 🎯

Industrial-grade local Ollama GUI with multi-model orchestration, live token streaming, graph-based output correlation, investigative file ingestion, agent pipelines, and GPU telemetry.

**Cyberpunk Industrial Theme • 100% Local • No External APIs**

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Node.js 16+
- Ollama installed and running

### macOS / Linux
```bash
chmod +x run.sh
./run.sh
```

### Windows
```cmd
run.bat
```

## ✨ Features

- **Multi-Model Execution** - Run multiple models in parallel or chain them
- **Live Token Streaming** - Real-time output with latency metrics
- **Graph Visualization** - Auto-extract entities and relationships with Cytoscape.js
- **File Ingestion** - Drag & drop PDFs, images, text, DOCX with OCR support
- **Agent Orchestration** - Research, analysis, summary, and investigation agents
- **System Telemetry** - Real-time GPU, CPU, RAM, VRAM monitoring
- **Workspace Management** - Save and reload investigation sessions

## 📚 Documentation

See [USAGE.md](USAGE.md) for comprehensive documentation including:
- Complete feature guide
- API documentation
- Troubleshooting tips
- Customization options

## 🛠️ Technology Stack

**Backend:** Python + FastAPI + WebSockets + Asyncio  
**Frontend:** Electron + HTML + CSS + JavaScript  
**Graph Engine:** Cytoscape.js  
**Telemetry:** psutil + GPUtil  
**Integration:** Ollama API (localhost:11434)

## 📁 Project Structure

```
ollama-gui/
├── backend/           # FastAPI server
├── frontend/          # Electron app (HTML/CSS/JS)
├── ingestion/         # File processing (PDF, OCR, text)
├── graph/             # Entity extraction & graph building
├── agents/            # Investigative agent framework
├── telemetry/         # System monitoring
├── workspaces/        # Saved sessions
├── run.sh / run.bat   # Startup scripts
└── requirements.txt   # Python dependencies
```

## 🎨 Design

Cyberpunk industrial aesthetic with:
- Dark gunmetal background (#1a1d23)
- Amber/orange neon accents (#ff9500)
- Professional investigative interface
- Smooth animations and real-time updates

## 📄 License

MIT License - See LICENSE file

---

**Built for local-first AI workflows, OSINT investigations, and cyberpunk enthusiasts** 🔥
