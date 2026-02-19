# OLLAMA COMMAND CENTER

Industrial-grade local Ollama GUI with multi-model orchestration, live token streaming, graph-based output correlation, investigative file ingestion, agent pipelines, and GPU telemetry.

![Cyberpunk Industrial Theme](docs/screenshot.png)

## 🎯 Features

### Core Capabilities
- **Multi-Model Execution** - Run multiple Ollama models simultaneously
- **Live Token Streaming** - Real-time token output with latency metrics
- **Graph Visualization** - Automatic entity extraction and relationship mapping
- **File Ingestion** - Drag & drop PDFs, images, text files, transcripts
- **Agent Orchestration** - Launch investigative agents with model chaining
- **System Telemetry** - Real-time GPU, CPU, RAM, and VRAM monitoring
- **Workspace Management** - Save and reload investigation sessions

### Design
- **Cyberpunk Industrial Aesthetic** - Dark gunmetal with amber/orange neon accents
- **Professional Interface** - Built for investigative workflows and OSINT analysis
- **100% Local** - No external APIs, fully offline capable

## 🛠️ Technology Stack

**Backend:**
- Python 3.8+
- FastAPI for REST API
- WebSocket for real-time streaming
- Asyncio for concurrent operations

**Frontend:**
- Electron for desktop application
- HTML5/CSS3/JavaScript
- Cytoscape.js for graph visualization
- Chart.js for telemetry visualization

**Integration:**
- Ollama API (http://localhost:11434)
- Local file system for workspace management

## 📋 Prerequisites

Before running the Ollama Command Center, ensure you have:

1. **Python 3.8 or higher**
   ```bash
   python3 --version
   ```

2. **Node.js 16 or higher**
   ```bash
   node --version
   ```

3. **Ollama installed and running**
   - Download from: https://ollama.ai
   - Verify it's running:
     ```bash
     curl http://localhost:11434/api/tags
     ```

4. **(Optional) Tesseract OCR for image text extraction**
   - macOS: `brew install tesseract`
   - Windows: Download from https://github.com/UB-Mannheim/tesseract/wiki
   - Linux: `sudo apt-get install tesseract-ocr`

## 🚀 Quick Start

### macOS / Linux

1. Clone the repository:
   ```bash
   git clone https://github.com/gs-ai/ollama-gui.git
   cd ollama-gui
   ```

2. Make the run script executable:
   ```bash
   chmod +x run.sh
   ```

3. Run the application:
   ```bash
   ./run.sh
   ```

### Windows

1. Clone the repository:
   ```cmd
   git clone https://github.com/gs-ai/ollama-gui.git
   cd ollama-gui
   ```

2. Run the application:
   ```cmd
   run.bat
   ```

The backend will start on `http://localhost:8000` and the Electron frontend will open automatically.

## 📖 User Guide

### Model Selection

1. **View Available Models** - All Ollama models appear in the left panel
2. **Select Models** - Click to select one or multiple models
3. **Execution Modes:**
   - **SINGLE** - Execute one model at a time
   - **PARALLEL** - Run multiple models simultaneously
   - **CHAIN** - Sequential execution (output → next model input)

### Prompt Execution

1. Enter your prompt in the text area
2. Select your model(s) and execution mode
3. Click **EXECUTE** button
4. Watch live token streaming in the OUTPUT STREAM tab

### File Ingestion

1. **Drag & Drop** files into the drop zone, or click **Browse Files**
2. Supported formats:
   - **PDF** - Text extraction
   - **Images** (PNG, JPG, GIF, BMP) - OCR text extraction
   - **Text files** (TXT, MD) - Direct reading
   - **Word documents** (DOCX) - Text extraction
3. Ingested files are processed and indexed automatically
4. Extracted text can be used in prompts and analysis

### Graph Visualization

1. Execute prompts and generate outputs
2. Switch to **GRAPH VIEW** tab
3. Click **Build Graph** to extract entities and relationships
4. Interact with the graph:
   - **Zoom** - Mouse wheel
   - **Pan** - Click and drag
   - **Select nodes** - Click on nodes
   - **Fit to View** - Reset graph position

Nodes are color-coded by type:
- 🟢 Green - Emails
- 🔵 Blue - URLs
- 🟠 Orange - Named entities

### Agent Orchestration

1. Select an agent type:
   - **Research** - Gather information from multiple models
   - **Analysis** - Deep analysis of data
   - **Summary** - Condense content
   - **Investigation** - Multi-step investigative workflow

2. Select models to use
3. Enter task description
4. Click **Launch Agent**
5. View agent execution in OUTPUT STREAM tab
6. Check **EXECUTION LOGS** for detailed steps

### Workspace Management

1. **Create Workspace** - Enter name and click Create
2. **Select Workspace** - Click on workspace name
3. **Save Session** - Saves current state (models, outputs, files)
4. **Load Session** - Restores previous session state

Workspaces are stored in `./workspaces/` directory.

### System Telemetry

Real-time monitoring of:
- **CPU Usage** - Per-core and overall utilization
- **RAM Usage** - Memory consumption
- **VRAM Usage** - GPU memory (if NVIDIA GPU detected)
- **Disk Usage** - Storage utilization

Updates every second via WebSocket connection.

## 🗂️ Directory Structure

```
ollama-gui/
├── backend/              # Python FastAPI backend
│   └── main.py          # Main API server
├── frontend/            # Electron frontend
│   ├── index.html      # Main UI
│   ├── styles.css      # Cyberpunk styling
│   ├── app.js          # Application logic
│   └── main.js         # Electron main process
├── ingestion/           # File processing modules
│   └── file_processor.py
├── graph/               # Graph engine
│   ├── entity_extractor.py
│   └── graph_builder.py
├── agents/              # Agent framework
│   └── investigative_agent.py
├── telemetry/           # System monitoring
│   └── system_monitor.py
├── workspaces/          # Saved sessions (created at runtime)
├── models/              # Model metadata (created at runtime)
├── logs/                # Application logs (created at runtime)
├── requirements.txt     # Python dependencies
├── package.json         # Node.js dependencies
├── run.sh              # macOS/Linux startup script
├── run.bat             # Windows startup script
└── README.md           # This file
```

## 🔌 API Documentation

The backend exposes a REST API and WebSocket endpoints:

### REST Endpoints

- `GET /` - Health check
- `GET /api/models` - List available Ollama models
- `POST /api/generate` - Generate text (non-streaming)
- `POST /api/chain` - Execute model chaining pipeline
- `POST /api/ingest/file` - Upload and process file
- `POST /api/graph/build` - Build graph from entities
- `POST /api/agent/execute` - Execute investigative agent
- `GET /api/telemetry/system` - Get system telemetry
- `POST /api/workspace/create` - Create workspace
- `GET /api/workspace/list` - List workspaces
- `POST /api/workspace/{name}/save_session` - Save session
- `GET /api/workspace/{name}/sessions` - Get workspace sessions

### WebSocket Endpoints

- `ws://localhost:8000/ws/stream` - Live token streaming
- `ws://localhost:8000/ws/telemetry` - Real-time telemetry updates

Interactive API documentation available at: http://localhost:8000/docs

## 🎨 Customization

### Theming

Edit `frontend/styles.css` to customize colors:

```css
:root {
    --bg-primary: #1a1d23;      /* Main background */
    --bg-secondary: #252930;     /* Panel background */
    --accent-primary: #ff9500;   /* Orange accent */
    --text-primary: #e0e0e0;     /* Text color */
}
```

### Adding New Agent Types

1. Edit `agents/investigative_agent.py`
2. Add new agent method (e.g., `_custom_agent`)
3. Add agent type to frontend dropdown in `index.html`

### Extending File Support

1. Edit `ingestion/file_processor.py`
2. Add new file extension to `supported_types`
3. Implement processing method

## 🐛 Troubleshooting

### Backend won't start

- Check Python version: `python3 --version` (need 3.8+)
- Install dependencies: `pip install -r requirements.txt`
- Check port 8000 is available: `lsof -i :8000` (macOS/Linux)

### Ollama connection failed

- Verify Ollama is running: `curl http://localhost:11434/api/tags`
- Start Ollama: `ollama serve`
- Check Ollama has models: `ollama list`

### Frontend won't open

- Check Node.js version: `node --version` (need 16+)
- Install dependencies: `npm install`
- Run Electron directly: `npm start`

### OCR not working

- Install Tesseract OCR:
  - macOS: `brew install tesseract`
  - Linux: `sudo apt-get install tesseract-ocr`
  - Windows: Download from GitHub

### GPU telemetry unavailable

- Install GPUtil: `pip install GPUtil`
- NVIDIA GPU required for GPU metrics
- CPU/RAM telemetry works without GPU

## 📊 Performance Tips

1. **Model Selection** - Smaller models (7B) are faster than larger ones (70B)
2. **Parallel Execution** - Use parallel mode for independent queries
3. **Chain Execution** - Use chain mode when output feeds into next model
4. **File Processing** - Large PDFs may take time to process
5. **Graph Building** - Limit output size for faster graph generation

## 🔒 Security Notes

- **100% Local** - No data leaves your machine
- **No telemetry** - No external analytics or tracking
- **File Access** - Only processes files you explicitly upload
- **Workspace Privacy** - All sessions stored locally

## 🤝 Contributing

Contributions welcome! Areas for improvement:

- Enhanced NLP entity extraction (spaCy integration)
- Additional agent types
- More file format support
- Graph layout algorithms
- Export functionality
- Dark/light theme toggle

## 📄 License

MIT License - See LICENSE file for details

## 🙏 Acknowledgments

- **Ollama** - Local LLM runtime
- **FastAPI** - High-performance Python web framework
- **Electron** - Cross-platform desktop apps
- **Cytoscape.js** - Graph visualization library

## 📞 Support

For issues and questions:
- GitHub Issues: https://github.com/gs-ai/ollama-gui/issues
- Documentation: See this README

---

**Built for local-first AI workflows, OSINT investigations, and cyberpunk enthusiasts** 🚀
