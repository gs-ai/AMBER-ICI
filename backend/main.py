"""
Ollama GUI Command Center - Backend API
Industrial cyberpunk multi-model orchestration system
"""

import asyncio
import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set
from contextlib import asynccontextmanager

import aiohttp
import psutil
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# Import custom modules
import sys
sys.path.append(str(Path(__file__).parent.parent))

from ingestion.file_processor import FileProcessor
from graph.entity_extractor import EntityExtractor
from graph.graph_builder import GraphBuilder
from agents.investigative_agent import InvestigativeAgent
from telemetry.system_monitor import SystemMonitor

# Global state
active_connections: Set[WebSocket] = set()
running_models: Dict[str, Dict] = {}
workspace_path = Path(__file__).parent.parent / "workspaces"
workspace_path.mkdir(exist_ok=True)

# Initialize components
file_processor = FileProcessor()
entity_extractor = EntityExtractor()
graph_builder = GraphBuilder()
system_monitor = SystemMonitor()

# Ollama API base URL
OLLAMA_BASE_URL = "http://localhost:11434"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    # Startup
    print("🚀 Ollama GUI Command Center initializing...")
    print(f"📁 Workspace directory: {workspace_path}")
    yield
    # Shutdown
    print("🛑 Shutting down...")


app = FastAPI(
    title="Ollama GUI Command Center",
    description="Industrial cyberpunk multi-model orchestration system",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# MODELS & SCHEMAS
# ============================================================================

class ModelRequest(BaseModel):
    model: str
    prompt: str
    stream: bool = True
    options: Optional[Dict] = None


class ChainRequest(BaseModel):
    models: List[str]
    prompt: str
    chain_type: str = "sequential"  # sequential or parallel


class WorkspaceCreate(BaseModel):
    name: str
    description: Optional[str] = None


class AgentTask(BaseModel):
    agent_type: str
    task: str
    models: List[str]
    parameters: Optional[Dict] = None


# ============================================================================
# OLLAMA API INTEGRATION
# ============================================================================

async def get_ollama_models() -> List[Dict]:
    """Fetch available models from Ollama"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{OLLAMA_BASE_URL}/api/tags") as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("models", [])
                return []
    except Exception as e:
        print(f"Error fetching models: {e}")
        return []


async def stream_ollama_response(model: str, prompt: str, options: Optional[Dict] = None):
    """Stream responses from Ollama model"""
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": True
    }
    if options:
        payload["options"] = options
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{OLLAMA_BASE_URL}/api/generate",
                json=payload
            ) as response:
                async for line in response.content:
                    if line:
                        try:
                            data = json.loads(line)
                            yield data
                        except json.JSONDecodeError:
                            continue
    except Exception as e:
        yield {"error": str(e), "done": True}


# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "online",
        "service": "Ollama GUI Command Center",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    }


@app.get("/api/models")
async def list_models():
    """Get list of available Ollama models"""
    models = await get_ollama_models()
    return {"models": models}


@app.post("/api/generate")
async def generate_text(request: ModelRequest):
    """Generate text from a model (non-streaming)"""
    try:
        full_response = ""
        async for chunk in stream_ollama_response(request.model, request.prompt, request.options):
            if "response" in chunk:
                full_response += chunk["response"]
            if chunk.get("done", False):
                break
        
        return {
            "model": request.model,
            "response": full_response,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/chain")
async def chain_models(request: ChainRequest):
    """Execute model chaining pipeline"""
    results = []
    current_prompt = request.prompt
    
    try:
        if request.chain_type == "sequential":
            # Sequential execution - output of one feeds into next
            for model in request.models:
                response = ""
                async for chunk in stream_ollama_response(model, current_prompt):
                    if "response" in chunk:
                        response += chunk["response"]
                    if chunk.get("done", False):
                        break
                
                results.append({
                    "model": model,
                    "input": current_prompt,
                    "output": response,
                    "timestamp": datetime.now().isoformat()
                })
                current_prompt = response  # Feed output to next model
        
        elif request.chain_type == "parallel":
            # Parallel execution - same prompt to all models
            tasks = []
            for model in request.models:
                tasks.append(generate_parallel(model, current_prompt))
            
            parallel_results = await asyncio.gather(*tasks)
            for model, response in zip(request.models, parallel_results):
                results.append({
                    "model": model,
                    "input": current_prompt,
                    "output": response,
                    "timestamp": datetime.now().isoformat()
                })
        
        return {"chain_type": request.chain_type, "results": results}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def generate_parallel(model: str, prompt: str) -> str:
    """Helper for parallel generation"""
    response = ""
    async for chunk in stream_ollama_response(model, prompt):
        if "response" in chunk:
            response += chunk["response"]
        if chunk.get("done", False):
            break
    return response


# ============================================================================
# WEBSOCKET FOR LIVE TOKEN STREAMING
# ============================================================================

@app.websocket("/ws/stream")
async def websocket_stream(websocket: WebSocket):
    """WebSocket endpoint for live token streaming"""
    await websocket.accept()
    active_connections.add(websocket)
    
    try:
        while True:
            # Receive request from client
            data = await websocket.receive_text()
            request_data = json.loads(data)
            
            model = request_data.get("model")
            prompt = request_data.get("prompt")
            options = request_data.get("options")
            
            if not model or not prompt:
                await websocket.send_json({
                    "error": "Missing model or prompt",
                    "done": True
                })
                continue
            
            # Stream tokens back to client
            async for chunk in stream_ollama_response(model, prompt, options):
                await websocket.send_json({
                    "model": model,
                    "chunk": chunk,
                    "timestamp": time.time()
                })
                
                if chunk.get("done", False):
                    break
    
    except WebSocketDisconnect:
        active_connections.remove(websocket)
    except Exception as e:
        print(f"WebSocket error: {e}")
        if websocket in active_connections:
            active_connections.remove(websocket)


# ============================================================================
# FILE INGESTION ENDPOINTS
# ============================================================================

@app.post("/api/ingest/file")
async def ingest_file(file: UploadFile = File(...)):
    """Ingest and process uploaded file"""
    try:
        # Save uploaded file temporarily
        temp_path = Path("/tmp") / file.filename
        with open(temp_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        # Process file
        result = await file_processor.process_file(temp_path)
        
        # Extract entities from text
        if result.get("text"):
            entities = entity_extractor.extract_entities(result["text"])
            result["entities"] = entities
        
        # Clean up temp file
        temp_path.unlink()
        
        return result
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# GRAPH ENDPOINTS
# ============================================================================

@app.post("/api/graph/build")
async def build_graph(data: Dict):
    """Build graph from entities and relationships"""
    try:
        texts = data.get("texts", [])
        sources = data.get("sources", [])
        
        # Extract entities from all texts
        all_entities = []
        for i, text in enumerate(texts):
            entities = entity_extractor.extract_entities(text)
            source = sources[i] if i < len(sources) else f"source_{i}"
            for entity in entities:
                entity["source"] = source
            all_entities.extend(entities)
        
        # Build graph
        graph_data = graph_builder.build_graph(all_entities)
        
        return graph_data
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# AGENT ORCHESTRATION ENDPOINTS
# ============================================================================

@app.post("/api/agent/execute")
async def execute_agent(task: AgentTask):
    """Execute an investigative agent"""
    try:
        agent = InvestigativeAgent(
            agent_type=task.agent_type,
            models=task.models
        )
        
        result = await agent.execute(task.task, task.parameters or {})
        
        return result
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# TELEMETRY ENDPOINTS
# ============================================================================

@app.get("/api/telemetry/system")
async def get_system_telemetry():
    """Get current system telemetry"""
    try:
        telemetry = system_monitor.get_current_stats()
        return telemetry
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.websocket("/ws/telemetry")
async def websocket_telemetry(websocket: WebSocket):
    """WebSocket endpoint for real-time telemetry"""
    await websocket.accept()
    
    try:
        while True:
            telemetry = system_monitor.get_current_stats()
            await websocket.send_json(telemetry)
            await asyncio.sleep(1)  # Update every second
    
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"Telemetry WebSocket error: {e}")


# ============================================================================
# WORKSPACE ENDPOINTS
# ============================================================================

@app.post("/api/workspace/create")
async def create_workspace(workspace: WorkspaceCreate):
    """Create a new workspace/case folder"""
    try:
        ws_path = workspace_path / workspace.name
        ws_path.mkdir(exist_ok=True)
        
        # Create workspace metadata
        metadata = {
            "name": workspace.name,
            "description": workspace.description,
            "created_at": datetime.now().isoformat(),
            "files": [],
            "sessions": []
        }
        
        metadata_file = ws_path / "metadata.json"
        with open(metadata_file, "w") as f:
            json.dump(metadata, f, indent=2)
        
        return {"status": "created", "workspace": workspace.name, "path": str(ws_path)}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/workspace/list")
async def list_workspaces():
    """List all workspaces"""
    try:
        workspaces = []
        for ws_dir in workspace_path.iterdir():
            if ws_dir.is_dir():
                metadata_file = ws_dir / "metadata.json"
                if metadata_file.exists():
                    with open(metadata_file, "r") as f:
                        metadata = json.load(f)
                        workspaces.append(metadata)
        
        return {"workspaces": workspaces}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/workspace/{workspace_name}/save_session")
async def save_session(workspace_name: str, session_data: Dict):
    """Save a session to a workspace"""
    try:
        ws_path = workspace_path / workspace_name
        if not ws_path.exists():
            raise HTTPException(status_code=404, detail="Workspace not found")
        
        session_id = session_data.get("session_id", f"session_{int(time.time())}")
        session_file = ws_path / f"{session_id}.json"
        
        with open(session_file, "w") as f:
            json.dump(session_data, f, indent=2)
        
        return {"status": "saved", "session_id": session_id}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/workspace/{workspace_name}/sessions")
async def get_workspace_sessions(workspace_name: str):
    """Get all sessions from a workspace"""
    try:
        ws_path = workspace_path / workspace_name
        if not ws_path.exists():
            raise HTTPException(status_code=404, detail="Workspace not found")
        
        sessions = []
        for session_file in ws_path.glob("*.json"):
            if session_file.name != "metadata.json":
                with open(session_file, "r") as f:
                    session_data = json.load(f)
                    sessions.append(session_data)
        
        return {"sessions": sessions}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
