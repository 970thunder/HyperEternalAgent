"""
Web API for HyperEternalAgent visualization interface.

This module provides a FastAPI-based REST API for interacting with
the HyperEternalAgent system through a web interface.
"""

import asyncio
import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from ..core.types import Task, TaskStatus, TaskPriority
from ..core.main import HyperEternalAgent
from ..core.config import SystemConfig
from ..infrastructure.logging import get_logger

logger = get_logger(__name__)


# Pydantic models for API
class TaskCreateRequest(BaseModel):
    """Request model for creating a task."""
    task_type: str
    payload: Dict[str, Any] = {}
    priority: int = 5
    timeout: Optional[int] = None
    max_retries: int = 3


class FlowCreateRequest(BaseModel):
    """Request model for creating a flow."""
    flow_name: str
    input_data: Dict[str, Any] = {}


class AgentCreateRequest(BaseModel):
    """Request model for creating an agent."""
    agent_type: str
    agent_id: Optional[str] = None
    config: Dict[str, Any] = {}


class SystemConfigRequest(BaseModel):
    """Request model for system configuration."""
    name: str = "HyperEternalAgent"
    version: str = "1.0.0"


# Create FastAPI app
app = FastAPI(
    title="HyperEternalAgent API",
    description="API for the HyperEternalAgent multi-agent framework",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global system instance
_system: Optional[HyperEternalAgent] = None
_websocket_connections: List[WebSocket] = []


async def get_system() -> HyperEternalAgent:
    """Get or create the system instance."""
    global _system
    if _system is None:
        config = SystemConfig(name="WebAPI", version="1.0.0")
        _system = HyperEternalAgent(config=config)
        await _system.start()
    return _system


@app.on_event("startup")
async def startup_event():
    """Initialize on startup."""
    logger.info("web_api_starting")
    await get_system()


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    global _system
    if _system:
        await _system.stop()
    logger.info("web_api_stopped")


# ============== System Endpoints ==============

@app.get("/api/system/status")
async def get_system_status():
    """Get system status."""
    system = await get_system()
    status = system.get_status()
    return JSONResponse(content=status)


@app.get("/api/system/info")
async def get_system_info():
    """Get system information."""
    system = await get_system()
    return JSONResponse(content={
        "name": system.config.name,
        "version": system.config.version,
        "running": True,
        "timestamp": datetime.now().isoformat(),
    })


@app.post("/api/system/start")
async def start_system():
    """Start the system."""
    system = await get_system()
    await system.start()
    return JSONResponse(content={"status": "started"})


@app.post("/api/system/stop")
async def stop_system():
    """Stop the system."""
    system = await get_system()
    await system.stop()
    return JSONResponse(content={"status": "stopped"})


# ============== Task Endpoints ==============

@app.post("/api/tasks")
async def create_task(request: TaskCreateRequest):
    """Create and submit a new task."""
    system = await get_system()
    submission = await system.submit_task(
        task_type=request.task_type,
        payload=request.payload,
        priority=request.priority,
        timeout=request.timeout,
    )
    return JSONResponse(content={
        "task_id": submission.task_id,
        "status": "submitted",
    })


@app.get("/api/tasks/{task_id}")
async def get_task_status(task_id: str):
    """Get task status."""
    system = await get_system()
    status = await system.get_task_status(task_id)
    if status is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return JSONResponse(content={"task_id": task_id, "status": status.value})


@app.get("/api/tasks/{task_id}/result")
async def get_task_result(task_id: str):
    """Get task result."""
    system = await get_system()
    result = await system.get_task_result(task_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Result not found")
    return JSONResponse(content=result.to_dict())


@app.delete("/api/tasks/{task_id}")
async def cancel_task(task_id: str):
    """Cancel a task."""
    system = await get_system()
    success = await system.cancel_task(task_id)
    return JSONResponse(content={"task_id": task_id, "cancelled": success})


@app.get("/api/tasks")
async def list_tasks(status: Optional[str] = None):
    """List tasks."""
    system = await get_system()
    stats = await system.task_queue.get_stats()
    return JSONResponse(content=stats)


# ============== Flow Endpoints ==============

@app.post("/api/flows")
async def execute_flow(request: FlowCreateRequest):
    """Execute a flow."""
    system = await get_system()
    execution_id = await system.submit_flow(
        flow_name=request.flow_name,
        input_data=request.input_data,
    )
    return JSONResponse(content={
        "execution_id": execution_id,
        "status": "submitted",
    })


@app.get("/api/flows/{execution_id}/status")
async def get_flow_status(execution_id: str):
    """Get flow execution status."""
    system = await get_system()
    status = await system.flow_engine.get_status(execution_id)
    if status is None:
        raise HTTPException(status_code=404, detail="Flow execution not found")
    return JSONResponse(content=status)


@app.get("/api/flows")
async def list_flows():
    """List available flows."""
    system = await get_system()
    flows = list(system.flow_engine._flows.keys())
    return JSONResponse(content={"flows": flows})


# ============== Agent Endpoints ==============

@app.post("/api/agents")
async def create_agent(request: AgentCreateRequest):
    """Create a new agent."""
    system = await get_system()
    agent = await system.create_agent(
        agent_type=request.agent_type,
        agent_id=request.agent_id,
        config=request.config,
    )
    return JSONResponse(content={
        "agent_id": agent.agent_id,
        "agent_type": request.agent_type,
        "status": "created",
    })


@app.get("/api/agents")
async def list_agents():
    """List all agents."""
    system = await get_system()
    agents = await system.agent_manager.get_all_agents()
    return JSONResponse(content={
        "agents": [
            {
                "agent_id": a.agent_id,
                "state": a.state.value,
                "agent_type": a.agent_type.value,
            }
            for a in agents
        ]
    })


@app.get("/api/agents/{agent_id}")
async def get_agent(agent_id: str):
    """Get agent details."""
    system = await get_system()
    agent = await system.agent_manager.get_agent(agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    return JSONResponse(content={
        "agent_id": agent.agent_id,
        "state": agent.state.value,
        "agent_type": agent.agent_type.value,
        "capabilities": agent.capabilities.to_dict() if hasattr(agent.capabilities, 'to_dict') else {},
    })


@app.delete("/api/agents/{agent_id}")
async def destroy_agent(agent_id: str):
    """Destroy an agent."""
    system = await get_system()
    success = await system.agent_manager.destroy_agent(agent_id)
    return JSONResponse(content={"agent_id": agent_id, "destroyed": success})


@app.get("/api/agents/types")
async def list_agent_types():
    """List registered agent types."""
    system = await get_system()
    return JSONResponse(content={
        "types": list(system.agent_manager._agent_types.keys())
    })


# ============== State Endpoints ==============

@app.get("/api/state/{scope}/{key}")
async def get_state(scope: str, key: str, owner_id: Optional[str] = None):
    """Get state value."""
    from ..persistence.state_manager import StateScope
    system = await get_system()

    try:
        scope_enum = StateScope(scope)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid scope")

    value = await system.state_manager.get(key, scope_enum, owner_id)
    return JSONResponse(content={"key": key, "value": value})


@app.post("/api/state/{scope}/{key}")
async def set_state(scope: str, key: str, value: Dict[str, Any], owner_id: Optional[str] = None, ttl: Optional[int] = None):
    """Set state value."""
    from ..persistence.state_manager import StateScope
    system = await get_system()

    try:
        scope_enum = StateScope(scope)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid scope")

    await system.state_manager.set(key, value, scope_enum, owner_id, ttl)
    return JSONResponse(content={"key": key, "status": "set"})


@app.delete("/api/state/{scope}/{key}")
async def delete_state(scope: str, key: str, owner_id: Optional[str] = None):
    """Delete state value."""
    from ..persistence.state_manager import StateScope
    system = await get_system()

    try:
        scope_enum = StateScope(scope)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid scope")

    await system.state_manager.delete(key, scope_enum, owner_id)
    return JSONResponse(content={"key": key, "status": "deleted"})


# ============== Quality/Reflection Endpoints ==============

@app.post("/api/quality/assess")
async def assess_quality(content: str, context: Dict[str, Any] = {}):
    """Assess content quality."""
    system = await get_system()
    assessment = await system.quality_engine.assess(content, context)
    return JSONResponse(content=assessment.to_dict())


@app.post("/api/errors/detect")
async def detect_errors(content: str, context: Dict[str, Any] = {}):
    """Detect errors in content."""
    system = await get_system()
    errors = await system.error_detector.detect(content, context)
    return JSONResponse(content={
        "errors": [e.to_dict() for e in errors]
    })


# ============== WebSocket for Real-time Updates ==============

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates."""
    await websocket.accept()
    _websocket_connections.append(websocket)

    try:
        while True:
            # Wait for messages
            data = await websocket.receive_text()

            # Parse command
            try:
                command = json.loads(data)
                response = await handle_websocket_command(command)
                await websocket.send_json(response)
            except json.JSONDecodeError:
                await websocket.send_json({"error": "Invalid JSON"})

    except WebSocketDisconnect:
        _websocket_connections.remove(websocket)


async def handle_websocket_command(command: Dict[str, Any]) -> Dict[str, Any]:
    """Handle WebSocket command."""
    cmd_type = command.get("type", "")

    if cmd_type == "ping":
        return {"type": "pong", "timestamp": datetime.now().isoformat()}

    elif cmd_type == "get_status":
        system = await get_system()
        return {"type": "status", "data": system.get_status()}

    elif cmd_type == "get_stats":
        system = await get_system()
        queue_stats = await system.task_queue.get_stats()
        return {"type": "stats", "data": queue_stats}

    else:
        return {"type": "error", "message": f"Unknown command: {cmd_type}"}


async def broadcast_update(message: Dict[str, Any]) -> None:
    """Broadcast update to all WebSocket connections."""
    for connection in _websocket_connections:
        try:
            await connection.send_json(message)
        except Exception:
            pass  # Connection might be closed


# ============== Serve Static Files ==============

# Mount static files (will be created in next step)
# app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the main dashboard page."""
    html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>HyperEternalAgent Dashboard</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #eee;
            min-height: 100vh;
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }

        header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 20px 0;
            border-bottom: 1px solid rgba(255,255,255,0.1);
            margin-bottom: 30px;
        }

        h1 {
            font-size: 24px;
            font-weight: 600;
        }

        .status-badge {
            padding: 6px 12px;
            border-radius: 20px;
            font-size: 14px;
            font-weight: 500;
        }

        .status-running {
            background: #10b981;
            color: white;
        }

        .status-stopped {
            background: #ef4444;
            color: white;
        }

        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }

        .card {
            background: rgba(255,255,255,0.05);
            border-radius: 12px;
            padding: 20px;
            border: 1px solid rgba(255,255,255,0.1);
        }

        .card-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }

        .card-title {
            font-size: 16px;
            font-weight: 600;
            color: #94a3b8;
        }

        .card-value {
            font-size: 32px;
            font-weight: 700;
            color: #fff;
        }

        .stat-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 15px;
        }

        .stat-item {
            text-align: center;
        }

        .stat-value {
            font-size: 24px;
            font-weight: 600;
        }

        .stat-label {
            font-size: 12px;
            color: #94a3b8;
            margin-top: 4px;
        }

        .task-list {
            list-style: none;
        }

        .task-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 12px;
            background: rgba(255,255,255,0.03);
            border-radius: 8px;
            margin-bottom: 8px;
        }

        .task-id {
            font-family: monospace;
            font-size: 13px;
        }

        .task-status {
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: 500;
        }

        .status-pending { background: #fbbf24; color: #000; }
        .status-running { background: #3b82f6; color: #fff; }
        .status-completed { background: #10b981; color: #fff; }
        .status-failed { background: #ef4444; color: #fff; }

        .btn {
            padding: 10px 20px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 500;
            transition: all 0.2s;
        }

        .btn-primary {
            background: #3b82f6;
            color: white;
        }

        .btn-primary:hover {
            background: #2563eb;
        }

        .btn-danger {
            background: #ef4444;
            color: white;
        }

        .form-group {
            margin-bottom: 15px;
        }

        .form-label {
            display: block;
            margin-bottom: 5px;
            font-size: 14px;
            color: #94a3b8;
        }

        .form-input, .form-textarea, .form-select {
            width: 100%;
            padding: 10px;
            border: 1px solid rgba(255,255,255,0.2);
            border-radius: 8px;
            background: rgba(255,255,255,0.05);
            color: #fff;
            font-size: 14px;
        }

        .form-textarea {
            min-height: 100px;
            resize: vertical;
        }

        .tabs {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
        }

        .tab {
            padding: 10px 20px;
            background: rgba(255,255,255,0.05);
            border: none;
            border-radius: 8px;
            color: #94a3b8;
            cursor: pointer;
            font-size: 14px;
            transition: all 0.2s;
        }

        .tab.active {
            background: #3b82f6;
            color: white;
        }

        .tab:hover:not(.active) {
            background: rgba(255,255,255,0.1);
        }

        .hidden {
            display: none;
        }

        .log-container {
            background: #0f172a;
            border-radius: 8px;
            padding: 15px;
            max-height: 300px;
            overflow-y: auto;
            font-family: monospace;
            font-size: 13px;
        }

        .log-entry {
            margin-bottom: 5px;
        }

        .log-time {
            color: #64748b;
        }

        .log-level {
            font-weight: 600;
        }

        .log-info { color: #3b82f6; }
        .log-warn { color: #fbbf24; }
        .log-error { color: #ef4444; }

        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }

        .loading {
            animation: pulse 1.5s infinite;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>HyperEternalAgent Dashboard</h1>
            <span id="system-status" class="status-badge status-running">Running</span>
        </header>

        <div class="tabs">
            <button class="tab active" onclick="showTab('overview')">Overview</button>
            <button class="tab" onclick="showTab('tasks')">Tasks</button>
            <button class="tab" onclick="showTab('agents')">Agents</button>
            <button class="tab" onclick="showTab('flows')">Flows</button>
        </div>

        <!-- Overview Tab -->
        <div id="tab-overview" class="tab-content">
            <div class="grid">
                <div class="card">
                    <div class="card-header">
                        <span class="card-title">System Status</span>
                    </div>
                    <div class="stat-grid">
                        <div class="stat-item">
                            <div class="stat-value" id="stat-agents">0</div>
                            <div class="stat-label">Active Agents</div>
                        </div>
                        <div class="stat-item">
                            <div class="stat-value" id="stat-tasks">0</div>
                            <div class="stat-label">Total Tasks</div>
                        </div>
                        <div class="stat-item">
                            <div class="stat-value" id="stat-pending">0</div>
                            <div class="stat-label">Pending</div>
                        </div>
                        <div class="stat-item">
                            <div class="stat-value" id="stat-completed">0</div>
                            <div class="stat-label">Completed</div>
                        </div>
                    </div>
                </div>

                <div class="card">
                    <div class="card-header">
                        <span class="card-title">Recent Tasks</span>
                    </div>
                    <ul class="task-list" id="recent-tasks">
                        <li class="task-item">Loading...</li>
                    </ul>
                </div>

                <div class="card">
                    <div class="card-header">
                        <span class="card-title">Activity Log</span>
                    </div>
                    <div class="log-container" id="activity-log">
                        <div class="log-entry">
                            <span class="log-time">--:--:--</span>
                            <span class="log-level log-info">[INFO]</span>
                            Connecting...
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Tasks Tab -->
        <div id="tab-tasks" class="tab-content hidden">
            <div class="grid">
                <div class="card">
                    <div class="card-header">
                        <span class="card-title">Create Task</span>
                    </div>
                    <form id="create-task-form">
                        <div class="form-group">
                            <label class="form-label">Task Type</label>
                            <select class="form-select" id="task-type" required>
                                <option value="">Select type...</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label class="form-label">Payload (JSON)</label>
                            <textarea class="form-textarea" id="task-payload">{}</textarea>
                        </div>
                        <div class="form-group">
                            <label class="form-label">Priority</label>
                            <select class="form-select" id="task-priority">
                                <option value="0">Low</option>
                                <option value="5" selected>Normal</option>
                                <option value="10">High</option>
                                <option value="15">Critical</option>
                                <option value="20">Urgent</option>
                            </select>
                        </div>
                        <button type="submit" class="btn btn-primary">Submit Task</button>
                    </form>
                </div>

                <div class="card">
                    <div class="card-header">
                        <span class="card-title">Task Queue</span>
                    </div>
                    <ul class="task-list" id="task-queue">
                        <li class="task-item">Loading...</li>
                    </ul>
                </div>
            </div>
        </div>

        <!-- Agents Tab -->
        <div id="tab-agents" class="tab-content hidden">
            <div class="grid">
                <div class="card">
                    <div class="card-header">
                        <span class="card-title">Create Agent</span>
                    </div>
                    <form id="create-agent-form">
                        <div class="form-group">
                            <label class="form-label">Agent Type</label>
                            <select class="form-select" id="agent-type" required>
                                <option value="">Select type...</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label class="form-label">Agent ID (optional)</label>
                            <input type="text" class="form-input" id="agent-id" placeholder="Auto-generated if empty">
                        </div>
                        <button type="submit" class="btn btn-primary">Create Agent</button>
                    </form>
                </div>

                <div class="card">
                    <div class="card-header">
                        <span class="card-title">Active Agents</span>
                    </div>
                    <ul class="task-list" id="agent-list">
                        <li class="task-item">Loading...</li>
                    </ul>
                </div>
            </div>
        </div>

        <!-- Flows Tab -->
        <div id="tab-flows" class="tab-content hidden">
            <div class="grid">
                <div class="card">
                    <div class="card-header">
                        <span class="card-title">Execute Flow</span>
                    </div>
                    <form id="execute-flow-form">
                        <div class="form-group">
                            <label class="form-label">Flow Name</label>
                            <select class="form-select" id="flow-name" required>
                                <option value="">Select flow...</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label class="form-label">Input Data (JSON)</label>
                            <textarea class="form-textarea" id="flow-input">{}</textarea>
                        </div>
                        <button type="submit" class="btn btn-primary">Execute Flow</button>
                    </form>
                </div>

                <div class="card">
                    <div class="card-header">
                        <span class="card-title">Available Flows</span>
                    </div>
                    <ul class="task-list" id="flow-list">
                        <li class="task-item">Loading...</li>
                    </ul>
                </div>
            </div>
        </div>
    </div>

    <script>
        // State
        let ws = null;
        let systemStatus = 'running';

        // Initialize
        document.addEventListener('DOMContentLoaded', () => {
            connectWebSocket();
            loadInitialData();
            setupForms();
        });

        // WebSocket connection
        function connectWebSocket() {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            ws = new WebSocket(`${protocol}//${window.location.host}/ws`);

            ws.onopen = () => {
                addLog('info', 'WebSocket connected');
                ws.send(JSON.stringify({type: 'get_status'}));
            };

            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                handleWebSocketMessage(data);
            };

            ws.onerror = (error) => {
                addLog('error', 'WebSocket error');
            };

            ws.onclose = () => {
                addLog('warn', 'WebSocket disconnected, reconnecting...');
                setTimeout(connectWebSocket, 3000);
            };
        }

        function handleWebSocketMessage(data) {
            if (data.type === 'status') {
                updateSystemStatus(data.data);
            } else if (data.type === 'stats') {
                updateStats(data.data);
            }
        }

        // API calls
        async function fetchAPI(endpoint, options = {}) {
            const response = await fetch(endpoint, {
                ...options,
                headers: {
                    'Content-Type': 'application/json',
                    ...options.headers
                }
            });
            return response.json();
        }

        async function loadInitialData() {
            try {
                // Load system status
                const status = await fetchAPI('/api/system/status');
                updateSystemStatus(status);

                // Load agent types
                const types = await fetchAPI('/api/agents/types');
                const agentTypeSelect = document.getElementById('agent-type');
                types.types.forEach(type => {
                    const option = document.createElement('option');
                    option.value = type;
                    option.textContent = type;
                    agentTypeSelect.appendChild(option);
                });

                // Use agent types for task types too
                const taskTypeSelect = document.getElementById('task-type');
                types.types.forEach(type => {
                    const option = document.createElement('option');
                    option.value = type;
                    option.textContent = type;
                    taskTypeSelect.appendChild(option);
                });

                // Load agents
                const agents = await fetchAPI('/api/agents');
                updateAgentList(agents.agents);

                // Load flows
                const flows = await fetchAPI('/api/flows');
                updateFlowList(flows.flows);

                // Load task stats
                const stats = await fetchAPI('/api/tasks');
                updateStats(stats);

            } catch (error) {
                addLog('error', `Failed to load data: ${error.message}`);
            }
        }

        // Form handlers
        function setupForms() {
            // Create task form
            document.getElementById('create-task-form').addEventListener('submit', async (e) => {
                e.preventDefault();
                const taskType = document.getElementById('task-type').value;
                const payload = JSON.parse(document.getElementById('task-payload').value || '{}');
                const priority = parseInt(document.getElementById('task-priority').value);

                try {
                    const result = await fetchAPI('/api/tasks', {
                        method: 'POST',
                        body: JSON.stringify({
                            task_type: taskType,
                            payload: payload,
                            priority: priority
                        })
                    });
                    addLog('info', `Task created: ${result.task_id}`);
                } catch (error) {
                    addLog('error', `Failed to create task: ${error.message}`);
                }
            });

            // Create agent form
            document.getElementById('create-agent-form').addEventListener('submit', async (e) => {
                e.preventDefault();
                const agentType = document.getElementById('agent-type').value;
                const agentId = document.getElementById('agent-id').value || null;

                try {
                    const result = await fetchAPI('/api/agents', {
                        method: 'POST',
                        body: JSON.stringify({
                            agent_type: agentType,
                            agent_id: agentId,
                            config: {}
                        })
                    });
                    addLog('info', `Agent created: ${result.agent_id}`);
                    loadInitialData(); // Refresh list
                } catch (error) {
                    addLog('error', `Failed to create agent: ${error.message}`);
                }
            });

            // Execute flow form
            document.getElementById('execute-flow-form').addEventListener('submit', async (e) => {
                e.preventDefault();
                const flowName = document.getElementById('flow-name').value;
                const inputData = JSON.parse(document.getElementById('flow-input').value || '{}');

                try {
                    const result = await fetchAPI('/api/flows', {
                        method: 'POST',
                        body: JSON.stringify({
                            flow_name: flowName,
                            input_data: inputData
                        })
                    });
                    addLog('info', `Flow started: ${result.execution_id}`);
                } catch (error) {
                    addLog('error', `Failed to execute flow: ${error.message}`);
                }
            });
        }

        // UI Updates
        function updateSystemStatus(status) {
            const badge = document.getElementById('system-status');
            if (status.running) {
                badge.textContent = 'Running';
                badge.className = 'status-badge status-running';
            } else {
                badge.textContent = 'Stopped';
                badge.className = 'status-badge status-stopped';
            }
        }

        function updateStats(stats) {
            document.getElementById('stat-agents').textContent = stats.active_agents || 0;
            document.getElementById('stat-tasks').textContent = stats.total_tasks || 0;
            document.getElementById('stat-pending').textContent = stats.pending || 0;
            document.getElementById('stat-completed').textContent = stats.completed || 0;
        }

        function updateAgentList(agents) {
            const list = document.getElementById('agent-list');
            if (agents.length === 0) {
                list.innerHTML = '<li class="task-item">No agents</li>';
                return;
            }

            list.innerHTML = agents.map(agent => `
                <li class="task-item">
                    <span class="task-id">${agent.agent_id}</span>
                    <span class="task-status status-${agent.state}">${agent.state}</span>
                </li>
            `).join('');

            document.getElementById('stat-agents').textContent = agents.length;
        }

        function updateFlowList(flows) {
            const list = document.getElementById('flow-list');
            const select = document.getElementById('flow-name');

            if (flows.length === 0) {
                list.innerHTML = '<li class="task-item">No flows defined</li>';
                return;
            }

            list.innerHTML = flows.map(flow => `
                <li class="task-item">
                    <span>${flow}</span>
                </li>
            `).join('');

            select.innerHTML = '<option value="">Select flow...</option>';
            flows.forEach(flow => {
                const option = document.createElement('option');
                option.value = flow;
                option.textContent = flow;
                select.appendChild(option);
            });
        }

        function addLog(level, message) {
            const log = document.getElementById('activity-log');
            const time = new Date().toLocaleTimeString();
            const entry = document.createElement('div');
            entry.className = 'log-entry';
            entry.innerHTML = `
                <span class="log-time">${time}</span>
                <span class="log-level log-${level}">[${level.toUpperCase()}]</span>
                ${message}
            `;
            log.insertBefore(entry, log.firstChild);
        }

        // Tab switching
        function showTab(tabName) {
            // Hide all tabs
            document.querySelectorAll('.tab-content').forEach(el => el.classList.add('hidden'));
            document.querySelectorAll('.tab').forEach(el => el.classList.remove('active'));

            // Show selected tab
            document.getElementById(`tab-${tabName}`).classList.remove('hidden');
            event.target.classList.add('active');
        }
    </script>
</body>
</html>
    """
    return HTMLResponse(content=html_content)


# Error handlers
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error("unhandled_exception", error=str(exc))
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc)}
    )


def run_server(host: str = "0.0.0.0", port: int = 8000):
    """Run the web server."""
    import uvicorn
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    run_server()
