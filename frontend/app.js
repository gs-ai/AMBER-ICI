/**
 * Ollama Command Center - Main Application Logic
 * Handles UI interactions, API communication, and real-time streaming
 */

const API_BASE = 'http://localhost:8000';
const WS_BASE = 'ws://localhost:8000';

// Application state
const state = {
    selectedModels: new Set(),
    executionMode: 'single',
    uploadedFiles: [],
    currentWorkspace: null,
    cy: null, // Cytoscape instance
    telemetryWs: null,
    streamWs: null,
    logs: []
};

// ============================================================================
// INITIALIZATION
// ============================================================================

document.addEventListener('DOMContentLoaded', () => {
    console.log('🚀 Ollama Command Center initializing...');
    
    initializeUI();
    loadModels();
    initializeGraph();
    connectTelemetry();
    loadWorkspaces();
    
    console.log('✅ Command Center ready');
});

// ============================================================================
// UI INITIALIZATION
// ============================================================================

function initializeUI() {
    // Tab switching
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', () => switchTab(btn.dataset.tab));
    });
    
    // Execution mode buttons
    document.querySelectorAll('.mode-btn').forEach(btn => {
        btn.addEventListener('click', () => setExecutionMode(btn.dataset.mode));
    });
    
    // File upload
    const dropZone = document.getElementById('dropZone');
    const fileInput = document.getElementById('fileInput');
    const browseBtn = document.getElementById('browseFiles');
    
    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('drag-over');
    });
    
    dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('drag-over');
    });
    
    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('drag-over');
        handleFiles(Array.from(e.dataTransfer.files));
    });
    
    browseBtn.addEventListener('click', () => fileInput.click());
    fileInput.addEventListener('change', (e) => {
        handleFiles(Array.from(e.target.files));
    });
    
    // Execute button
    document.getElementById('executeBtn').addEventListener('click', executePrompt);
    
    // Clear button
    document.getElementById('clearBtn').addEventListener('click', clearOutput);
    
    // Agent launch
    document.getElementById('launchAgent').addEventListener('click', launchAgent);
    
    // Graph controls
    document.getElementById('fitGraph').addEventListener('click', () => {
        if (state.cy) state.cy.fit();
    });
    document.getElementById('clearGraph').addEventListener('click', clearGraph);
    document.getElementById('buildGraph').addEventListener('click', buildGraphFromOutputs);
    
    // Workspace controls
    document.getElementById('createWorkspace').addEventListener('click', createWorkspace);
    document.getElementById('saveSession').addEventListener('click', saveSession);
    document.getElementById('loadSession').addEventListener('click', loadSession);
    
    // Panel toggles
    document.getElementById('toggleTelemetry').addEventListener('click', () => {
        document.getElementById('telemetryPanel').classList.toggle('hidden');
    });
    document.getElementById('toggleWorkspace').addEventListener('click', () => {
        document.getElementById('workspacePanel').classList.toggle('hidden');
    });
}

// ============================================================================
// MODELS
// ============================================================================

async function loadModels() {
    try {
        const response = await fetch(`${API_BASE}/api/models`);
        const data = await response.json();
        
        const modelList = document.getElementById('modelList');
        modelList.innerHTML = '';
        
        if (data.models && data.models.length > 0) {
            data.models.forEach(model => {
                const modelItem = createModelItem(model);
                modelList.appendChild(modelItem);
            });
        } else {
            modelList.innerHTML = '<div class="loading">No models available. Make sure Ollama is running.</div>';
        }
    } catch (error) {
        console.error('Error loading models:', error);
        showNotification('Failed to load models. Is Ollama running?', 'error');
    }
}

function createModelItem(model) {
    const div = document.createElement('div');
    div.className = 'model-item';
    div.innerHTML = `
        <div class="model-checkbox"></div>
        <div class="model-name">${model.name}</div>
    `;
    
    div.addEventListener('click', () => toggleModelSelection(model.name, div));
    
    return div;
}

function toggleModelSelection(modelName, element) {
    if (state.selectedModels.has(modelName)) {
        state.selectedModels.delete(modelName);
        element.classList.remove('selected');
    } else {
        // In single mode, only allow one model
        if (state.executionMode === 'single') {
            state.selectedModels.clear();
            document.querySelectorAll('.model-item').forEach(item => {
                item.classList.remove('selected');
            });
        }
        state.selectedModels.add(modelName);
        element.classList.add('selected');
    }
}

function setExecutionMode(mode) {
    state.executionMode = mode;
    
    document.querySelectorAll('.mode-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    document.querySelector(`[data-mode="${mode}"]`).classList.add('active');
    
    // If switching to single mode, keep only first selected model
    if (mode === 'single' && state.selectedModels.size > 1) {
        const firstModel = Array.from(state.selectedModels)[0];
        state.selectedModels.clear();
        state.selectedModels.add(firstModel);
        
        document.querySelectorAll('.model-item').forEach(item => {
            const modelName = item.querySelector('.model-name').textContent;
            if (modelName === firstModel) {
                item.classList.add('selected');
            } else {
                item.classList.remove('selected');
            }
        });
    }
}

// ============================================================================
// EXECUTION
// ============================================================================

async function executePrompt() {
    const prompt = document.getElementById('promptInput').value.trim();
    
    if (!prompt) {
        showNotification('Please enter a prompt', 'warning');
        return;
    }
    
    if (state.selectedModels.size === 0) {
        showNotification('Please select at least one model', 'warning');
        return;
    }
    
    const models = Array.from(state.selectedModels);
    
    if (state.executionMode === 'single') {
        await executeSingle(models[0], prompt);
    } else if (state.executionMode === 'parallel') {
        await executeParallel(models, prompt);
    } else if (state.executionMode === 'chain') {
        await executeChain(models, prompt);
    }
}

async function executeSingle(model, prompt) {
    const streamId = addOutputStream(model);
    logExecution(`Executing single model: ${model}`);
    
    try {
        const ws = new WebSocket(`${WS_BASE}/ws/stream`);
        
        ws.onopen = () => {
            ws.send(JSON.stringify({ model, prompt }));
        };
        
        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            
            if (data.chunk && data.chunk.response) {
                appendToStream(streamId, data.chunk.response);
            }
            
            if (data.chunk && data.chunk.done) {
                updateStreamStatus(streamId, 'completed');
                ws.close();
                logExecution(`Completed: ${model}`, 'success');
            }
        };
        
        ws.onerror = (error) => {
            console.error('WebSocket error:', error);
            updateStreamStatus(streamId, 'error');
            logExecution(`Error in ${model}`, 'error');
        };
        
    } catch (error) {
        console.error('Execution error:', error);
        showNotification(`Execution failed: ${error.message}`, 'error');
    }
}

async function executeParallel(models, prompt) {
    logExecution(`Executing parallel: ${models.join(', ')}`);
    
    const promises = models.map(model => executeSingle(model, prompt));
    await Promise.all(promises);
    
    logExecution('Parallel execution completed', 'success');
}

async function executeChain(models, prompt) {
    logExecution(`Executing chain: ${models.join(' → ')}`);
    
    try {
        const response = await fetch(`${API_BASE}/api/chain`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                models,
                prompt,
                chain_type: 'sequential'
            })
        });
        
        const data = await response.json();
        
        data.results.forEach((result, index) => {
            const streamId = addOutputStream(result.model);
            appendToStream(streamId, result.output);
            updateStreamStatus(streamId, 'completed');
            logExecution(`Chain step ${index + 1} completed: ${result.model}`, 'success');
        });
        
        logExecution('Chain execution completed', 'success');
        
    } catch (error) {
        console.error('Chain execution error:', error);
        showNotification(`Chain execution failed: ${error.message}`, 'error');
    }
}

// ============================================================================
// OUTPUT STREAMS
// ============================================================================

function addOutputStream(modelName) {
    const streamId = `stream_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    const container = document.getElementById('outputStreams');
    
    const streamDiv = document.createElement('div');
    streamDiv.className = 'output-stream';
    streamDiv.id = streamId;
    streamDiv.innerHTML = `
        <div class="stream-header">
            <div class="stream-model">${modelName}</div>
            <div class="stream-status">streaming...</div>
        </div>
        <div class="stream-content"></div>
        <div class="stream-metrics">
            <span>Tokens: <span class="token-count">0</span></span>
            <span>Time: <span class="elapsed-time">0s</span></span>
        </div>
    `;
    
    container.appendChild(streamDiv);
    
    // Start elapsed time counter
    const startTime = Date.now();
    const interval = setInterval(() => {
        const elapsed = Math.floor((Date.now() - startTime) / 1000);
        const timeSpan = streamDiv.querySelector('.elapsed-time');
        if (timeSpan) timeSpan.textContent = `${elapsed}s`;
    }, 1000);
    
    streamDiv.dataset.interval = interval;
    
    return streamId;
}

function appendToStream(streamId, text) {
    const stream = document.getElementById(streamId);
    if (!stream) return;
    
    const content = stream.querySelector('.stream-content');
    content.textContent += text;
    content.scrollTop = content.scrollHeight;
    
    // Update token count (approximate)
    const tokenCount = content.textContent.split(/\s+/).length;
    stream.querySelector('.token-count').textContent = tokenCount;
}

function updateStreamStatus(streamId, status) {
    const stream = document.getElementById(streamId);
    if (!stream) return;
    
    const statusSpan = stream.querySelector('.stream-status');
    statusSpan.textContent = status;
    
    // Clear interval
    if (stream.dataset.interval) {
        clearInterval(parseInt(stream.dataset.interval));
    }
}

function clearOutput() {
    document.getElementById('outputStreams').innerHTML = '';
    document.getElementById('promptInput').value = '';
    showNotification('Output cleared', 'success');
}

// ============================================================================
// FILE HANDLING
// ============================================================================

async function handleFiles(files) {
    for (const file of files) {
        await uploadFile(file);
    }
}

async function uploadFile(file) {
    const formData = new FormData();
    formData.append('file', file);
    
    try {
        showNotification(`Uploading ${file.name}...`, 'info');
        
        const response = await fetch(`${API_BASE}/api/ingest/file`, {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        if (result.success) {
            state.uploadedFiles.push({ name: file.name, ...result });
            addFileToList(file.name, result);
            showNotification(`File processed: ${file.name}`, 'success');
            logExecution(`File ingested: ${file.name}`, 'success');
        } else {
            showNotification(`File processing failed: ${result.error}`, 'error');
        }
        
    } catch (error) {
        console.error('File upload error:', error);
        showNotification(`Upload failed: ${error.message}`, 'error');
    }
}

function addFileToList(filename, data) {
    const fileList = document.getElementById('fileList');
    
    const fileItem = document.createElement('div');
    fileItem.className = 'file-item';
    fileItem.innerHTML = `
        <span>${filename}</span>
        <span class="file-remove" onclick="removeFile('${filename}')">✕</span>
    `;
    
    fileList.appendChild(fileItem);
}

function removeFile(filename) {
    state.uploadedFiles = state.uploadedFiles.filter(f => f.name !== filename);
    
    const fileList = document.getElementById('fileList');
    const items = fileList.querySelectorAll('.file-item');
    items.forEach(item => {
        if (item.textContent.includes(filename)) {
            item.remove();
        }
    });
    
    showNotification(`Removed: ${filename}`, 'info');
}

// ============================================================================
// GRAPH VISUALIZATION
// ============================================================================

function initializeGraph() {
    const container = document.getElementById('graphContainer');
    
    state.cy = cytoscape({
        container: container,
        style: [
            {
                selector: 'node',
                style: {
                    'background-color': '#ff9500',
                    'label': 'data(label)',
                    'color': '#e0e0e0',
                    'text-valign': 'center',
                    'text-halign': 'center',
                    'font-size': '12px',
                    'width': '60px',
                    'height': '60px',
                    'border-width': '2px',
                    'border-color': '#ffb84d',
                    'text-outline-width': '2px',
                    'text-outline-color': '#1a1d23'
                }
            },
            {
                selector: 'edge',
                style: {
                    'width': 2,
                    'line-color': '#3d4149',
                    'target-arrow-color': '#3d4149',
                    'target-arrow-shape': 'triangle',
                    'curve-style': 'bezier'
                }
            },
            {
                selector: 'node[type="email"]',
                style: { 'background-color': '#4caf50' }
            },
            {
                selector: 'node[type="url"]',
                style: { 'background-color': '#2196f3' }
            },
            {
                selector: 'node[type="named_entity"]',
                style: { 'background-color': '#ff9500' }
            }
        ],
        layout: {
            name: 'cose',
            animate: true,
            animationDuration: 500
        }
    });
}

async function buildGraphFromOutputs() {
    const streams = document.querySelectorAll('.output-stream');
    if (streams.length === 0) {
        showNotification('No output streams to build graph from', 'warning');
        return;
    }
    
    const texts = [];
    const sources = [];
    
    streams.forEach((stream, index) => {
        const content = stream.querySelector('.stream-content').textContent;
        const model = stream.querySelector('.stream-model').textContent;
        texts.push(content);
        sources.push(model);
    });
    
    try {
        const response = await fetch(`${API_BASE}/api/graph/build`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ texts, sources })
        });
        
        const graphData = await response.json();
        
        renderGraph(graphData);
        showNotification('Graph built successfully', 'success');
        switchTab('graph');
        
    } catch (error) {
        console.error('Graph building error:', error);
        showNotification(`Failed to build graph: ${error.message}`, 'error');
    }
}

function renderGraph(graphData) {
    if (!state.cy) return;
    
    state.cy.elements().remove();
    
    const elements = [];
    
    // Add nodes
    graphData.nodes.forEach(node => {
        elements.push({
            data: {
                id: node.id,
                label: node.label,
                type: node.type,
                source: node.source
            }
        });
    });
    
    // Add edges
    graphData.edges.forEach(edge => {
        elements.push({
            data: {
                id: edge.id,
                source: edge.source,
                target: edge.target
            }
        });
    });
    
    state.cy.add(elements);
    state.cy.layout({ name: 'cose', animate: true }).run();
}

function clearGraph() {
    if (state.cy) {
        state.cy.elements().remove();
        showNotification('Graph cleared', 'info');
    }
}

// ============================================================================
// AGENTS
// ============================================================================

async function launchAgent() {
    const agentType = document.getElementById('agentType').value;
    const prompt = document.getElementById('promptInput').value.trim();
    
    if (!prompt) {
        showNotification('Please enter a task for the agent', 'warning');
        return;
    }
    
    if (state.selectedModels.size === 0) {
        showNotification('Please select at least one model', 'warning');
        return;
    }
    
    const models = Array.from(state.selectedModels);
    
    try {
        showNotification(`Launching ${agentType} agent...`, 'info');
        logExecution(`Agent launched: ${agentType}`, 'info');
        
        const response = await fetch(`${API_BASE}/api/agent/execute`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                agent_type: agentType,
                task: prompt,
                models: models,
                parameters: {}
            })
        });
        
        const result = await response.json();
        
        if (result.status === 'completed') {
            const streamId = addOutputStream(`[AGENT] ${agentType}`);
            appendToStream(streamId, result.output);
            updateStreamStatus(streamId, 'completed');
            
            showNotification('Agent completed successfully', 'success');
            logExecution(`Agent completed: ${agentType}`, 'success');
            
            // Log execution steps
            if (result.execution_log) {
                result.execution_log.forEach(log => {
                    logExecution(`[Agent] ${log.message}`, 'info');
                });
            }
        } else {
            showNotification(`Agent failed: ${result.error}`, 'error');
            logExecution(`Agent failed: ${result.error}`, 'error');
        }
        
    } catch (error) {
        console.error('Agent execution error:', error);
        showNotification(`Agent execution failed: ${error.message}`, 'error');
    }
}

// ============================================================================
// TELEMETRY
// ============================================================================

function connectTelemetry() {
    try {
        state.telemetryWs = new WebSocket(`${WS_BASE}/ws/telemetry`);
        
        state.telemetryWs.onmessage = (event) => {
            const data = JSON.parse(event.data);
            updateTelemetryDisplay(data);
        };
        
        state.telemetryWs.onerror = () => {
            console.log('Telemetry connection failed, retrying...');
            setTimeout(connectTelemetry, 5000);
        };
        
        state.telemetryWs.onclose = () => {
            setTimeout(connectTelemetry, 5000);
        };
        
    } catch (error) {
        console.error('Telemetry connection error:', error);
    }
}

function updateTelemetryDisplay(data) {
    // CPU
    if (data.cpu) {
        document.getElementById('cpuValue').textContent = `${data.cpu.usage_percent.toFixed(1)}%`;
        document.getElementById('cpuBar').style.width = `${data.cpu.usage_percent}%`;
    }
    
    // RAM
    if (data.memory) {
        document.getElementById('ramValue').textContent = `${data.memory.usage_percent.toFixed(1)}%`;
        document.getElementById('ramBar').style.width = `${data.memory.usage_percent}%`;
    }
    
    // VRAM/GPU
    if (data.gpu && data.gpu.available && data.gpu.gpus && data.gpu.gpus.length > 0) {
        const gpu = data.gpu.gpus[0];
        document.getElementById('vramValue').textContent = `${gpu.memory_usage_percent.toFixed(1)}%`;
        document.getElementById('vramBar').style.width = `${gpu.memory_usage_percent}%`;
        
        // GPU details
        const gpuDetails = document.getElementById('gpuDetails');
        gpuDetails.innerHTML = `
            <div style="margin-bottom: 0.5rem;"><strong>${gpu.name}</strong></div>
            <div>Memory: ${gpu.memory_used_mb.toFixed(0)} / ${gpu.memory_total_mb.toFixed(0)} MB</div>
            <div>Temperature: ${gpu.temperature_c}°C</div>
        `;
    } else {
        document.getElementById('vramValue').textContent = 'N/A';
        document.getElementById('vramBar').style.width = '0%';
    }
    
    // Disk
    if (data.disk) {
        document.getElementById('diskValue').textContent = `${data.disk.usage_percent.toFixed(1)}%`;
        document.getElementById('diskBar').style.width = `${data.disk.usage_percent}%`;
    }
}

// ============================================================================
// WORKSPACES
// ============================================================================

async function loadWorkspaces() {
    try {
        const response = await fetch(`${API_BASE}/api/workspace/list`);
        const data = await response.json();
        
        const workspaceList = document.getElementById('workspaceList');
        workspaceList.innerHTML = '';
        
        if (data.workspaces && data.workspaces.length > 0) {
            data.workspaces.forEach(ws => {
                const wsItem = document.createElement('div');
                wsItem.className = 'workspace-item';
                wsItem.textContent = ws.name;
                wsItem.addEventListener('click', () => selectWorkspace(ws.name, wsItem));
                workspaceList.appendChild(wsItem);
            });
        } else {
            workspaceList.innerHTML = '<div class="loading">No workspaces</div>';
        }
        
    } catch (error) {
        console.error('Error loading workspaces:', error);
    }
}

function selectWorkspace(name, element) {
    state.currentWorkspace = name;
    
    document.querySelectorAll('.workspace-item').forEach(item => {
        item.classList.remove('active');
    });
    element.classList.add('active');
    
    showNotification(`Workspace selected: ${name}`, 'success');
}

async function createWorkspace() {
    const name = document.getElementById('workspaceName').value.trim();
    
    if (!name) {
        showNotification('Please enter a workspace name', 'warning');
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/api/workspace/create`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, description: '' })
        });
        
        const result = await response.json();
        
        if (result.status === 'created') {
            showNotification(`Workspace created: ${name}`, 'success');
            document.getElementById('workspaceName').value = '';
            loadWorkspaces();
        }
        
    } catch (error) {
        console.error('Error creating workspace:', error);
        showNotification(`Failed to create workspace: ${error.message}`, 'error');
    }
}

async function saveSession() {
    if (!state.currentWorkspace) {
        showNotification('Please select a workspace first', 'warning');
        return;
    }
    
    const sessionData = {
        session_id: `session_${Date.now()}`,
        timestamp: new Date().toISOString(),
        selectedModels: Array.from(state.selectedModels),
        executionMode: state.executionMode,
        files: state.uploadedFiles.map(f => f.name),
        outputs: []
    };
    
    // Collect outputs
    document.querySelectorAll('.output-stream').forEach(stream => {
        const model = stream.querySelector('.stream-model').textContent;
        const content = stream.querySelector('.stream-content').textContent;
        sessionData.outputs.push({ model, content });
    });
    
    try {
        const response = await fetch(`${API_BASE}/api/workspace/${state.currentWorkspace}/save_session`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(sessionData)
        });
        
        const result = await response.json();
        
        if (result.status === 'saved') {
            showNotification('Session saved successfully', 'success');
            logExecution('Session saved', 'success');
        }
        
    } catch (error) {
        console.error('Error saving session:', error);
        showNotification(`Failed to save session: ${error.message}`, 'error');
    }
}

async function loadSession() {
    if (!state.currentWorkspace) {
        showNotification('Please select a workspace first', 'warning');
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/api/workspace/${state.currentWorkspace}/sessions`);
        const data = await response.json();
        
        if (data.sessions && data.sessions.length > 0) {
            // Load most recent session
            const session = data.sessions[data.sessions.length - 1];
            
            // Restore session state
            state.selectedModels = new Set(session.selectedModels || []);
            state.executionMode = session.executionMode || 'single';
            
            // Restore outputs
            clearOutput();
            if (session.outputs) {
                session.outputs.forEach(output => {
                    const streamId = addOutputStream(output.model);
                    appendToStream(streamId, output.content);
                    updateStreamStatus(streamId, 'loaded');
                });
            }
            
            showNotification('Session loaded successfully', 'success');
            logExecution('Session loaded', 'success');
        } else {
            showNotification('No sessions found in workspace', 'info');
        }
        
    } catch (error) {
        console.error('Error loading session:', error);
        showNotification(`Failed to load session: ${error.message}`, 'error');
    }
}

// ============================================================================
// LOGGING
// ============================================================================

function logExecution(message, level = 'info') {
    const timestamp = new Date().toISOString();
    const log = { timestamp, message, level };
    
    state.logs.push(log);
    
    const logsContainer = document.getElementById('executionLogs');
    const logEntry = document.createElement('div');
    logEntry.className = 'log-entry';
    logEntry.innerHTML = `
        <div class="log-timestamp">${new Date(timestamp).toLocaleTimeString()}</div>
        <div class="log-message log-level-${level}">${message}</div>
    `;
    
    logsContainer.appendChild(logEntry);
    logsContainer.scrollTop = logsContainer.scrollHeight;
    
    console.log(`[${level.toUpperCase()}] ${message}`);
}

// ============================================================================
// UI HELPERS
// ============================================================================

function switchTab(tabName) {
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');
    
    document.querySelectorAll('.tab-pane').forEach(pane => {
        pane.classList.remove('active');
    });
    document.getElementById(`${tabName}Tab`).classList.add('active');
}

function showNotification(message, type = 'info') {
    const container = document.getElementById('notifications');
    
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;
    
    container.appendChild(notification);
    
    setTimeout(() => {
        notification.style.opacity = '0';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}
