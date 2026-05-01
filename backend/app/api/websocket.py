# backend/app/api/websocket.py
"""
WebSocket endpoint for real-time agent updates, code streaming, and pipeline progress.

Protocol:
  Server → Client:
    {"type": "status"|"code"|"log"|"error"|"result"|"file"|"agent_action"|"notebook_cell",
     "agent": "...", "content": "...", "metadata": {}, "timestamp": "ISO8601"}

  Client → Server:
    {"type": "chat"|"command", "content": "...", "session_id": "uuid"}
"""
from datetime import datetime
import json
import logging
import re
from typing import Any, Dict, List

from fastapi import WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from app.infrastructure.memory import memory
from app.infrastructure.llm_router import llm_router
from app.models.schemas import WSClientMessage, WSServerMessage

logger = logging.getLogger(__name__)

# ── Regex to split LLM output into markdown + code blocks ──
_FENCED_BLOCK_RE = re.compile(
    r"(```(?:python|py)?\s*\n[\s\S]*?```)",
    re.IGNORECASE,
)

_CODE_CONTENT_RE = re.compile(
    r"```(?:python|py)?\s*\n([\s\S]*?)```",
    re.IGNORECASE,
)

# ── Autonomous system prompt injected for pipeline context ──
_AUTONOMOUS_SYSTEM_PROMPT = """\
You are DS-Copilot, an Autonomous Data Scientist with full code execution capabilities.

## Current Context
- You have access to a Python Notebook tool.
- Current file: '{filename}'
- Working directory: The sandbox contains the uploaded dataset.

## Objective
Your objective is to move through the data science lifecycle:
  Profiling → Cleaning → EDA → Feature Engineering → Modeling → Evaluation

## Rules
1. When the user starts a pipeline, **do not ask questions**. Execute code immediately.
2. Always provide complete, runnable Python code in fenced ```python blocks.
3. Use pandas, numpy, matplotlib, seaborn, and scikit-learn.
4. Start with `import pandas as pd` and `df = pd.read_csv('{filename}')`.
5. Each response should contain exactly ONE phase of the pipeline.
6. After each phase, state what you found and what you will do next.
7. Be concise in your explanations — let the code speak.
8. Alternate between brief explanations in markdown and code blocks.
"""

_DEFAULT_SYSTEM_PROMPT = """\
You are DS-Copilot, an expert data science assistant.
Help users with ML pipeline questions. Be concise.
When providing code, always use fenced ```python code blocks.
"""


def _build_system_prompt(filename: str | None = None) -> str:
    """Build the appropriate system prompt based on context."""
    if filename:
        return _AUTONOMOUS_SYSTEM_PROMPT.format(filename=filename)
    return _DEFAULT_SYSTEM_PROMPT


from app.agent.tools.notebook_utils import split_into_cells

async def _emit_notebook_cells(session_id: str, full_response: str, stage: str = ""):
    """
    Parse a full LLM response into mixed markdown/code cells and emit
    each as a notebook_cell event.
    """
    cells = split_into_cells(full_response)

    for i, cell in enumerate(cells):
        await manager.send_to_session(session_id, {
            "type": "notebook_cell",
            "agent": "assistant",
            "content": cell["content"],
            "metadata": {
                "cell_type": cell["type"],
                "stage": stage,
                "cell_index": i,
                "language": "python" if cell["type"] == "code" else "markdown",
            },
        })

class ConnectionManager:
    """Manages WebSocket connections per session."""

    def __init__(self):
        # session_id -> list of WebSocket connections
        self.active_connections: Dict[str, List[WebSocket]] = {}
        # session_id -> context metadata (uploaded file, pipeline state)
        self.session_context: Dict[str, Dict[str, Any]] = {}

    async def connect(self, websocket: WebSocket, session_id: str):
        """Accept and register a WebSocket connection."""
        await websocket.accept()
        if session_id not in self.active_connections:
            self.active_connections[session_id] = []
        self.active_connections[session_id].append(websocket)
        logger.info(f"[WS] Client connected to session: {session_id}")

        # Send welcome message
        await self._send_json(websocket, {
            "type": "status",
            "agent": "system",
            "content": "Connected to DS-Copilot",
            "metadata": {"session_id": session_id},
            "timestamp": datetime.utcnow().isoformat(),
        })

    def disconnect(self, websocket: WebSocket, session_id: str):
        """Remove a WebSocket connection."""
        if session_id in self.active_connections:
            if websocket in self.active_connections[session_id]:
                self.active_connections[session_id].remove(websocket)
            if not self.active_connections[session_id]:
                del self.active_connections[session_id]
        logger.info(f"[WS] Client disconnected from session: {session_id}")

    def set_context(self, session_id: str, key: str, value: Any):
        """Store session-level context (e.g., current filename)."""
        if session_id not in self.session_context:
            self.session_context[session_id] = {}
        self.session_context[session_id][key] = value

    def get_context(self, session_id: str) -> Dict[str, Any]:
        """Retrieve session-level context."""
        return self.session_context.get(session_id, {})

    async def send_progress_update(self, session_id: str, step_key: str, progress: int, message: str = ""):
        """Send a progress update for a specific pipeline step."""
        await self.send_to_session(session_id, {
            "type": "progress",
            "agent": "orchestrator",
            "content": message,
            "metadata": {
                "step": step_key,
                "progress": progress
            }
        })

    async def send_to_session(self, session_id: str, message: dict):
        """Send a message to all connections in a session."""
        payload = dict(message)
        if "timestamp" not in payload:
            payload["timestamp"] = datetime.utcnow().isoformat()

        try:
            payload = WSServerMessage.model_validate(payload).model_dump(mode="python")
        except ValidationError:
            # Fallback to raw payload to avoid dropping messages from legacy paths.
            logger.debug("[WS] Non-standard message payload: %s", payload, exc_info=True)

        connections = self.active_connections.get(session_id, [])
        disconnected = []

        for ws in connections:
            try:
                await self._send_json(ws, payload)
            except Exception:
                disconnected.append(ws)

        # Clean up dead connections
        for ws in disconnected:
            self.disconnect(ws, session_id)

    async def broadcast(self, message: dict):
        """Send a message to ALL connected clients."""
        if "timestamp" not in message:
            message["timestamp"] = datetime.utcnow().isoformat()

        for session_id in list(self.active_connections.keys()):
            await self.send_to_session(session_id, message)

    async def _send_json(self, websocket: WebSocket, data: dict):
        """Send JSON data through WebSocket."""
        await websocket.send_json(data)

    def get_connection_count(self, session_id: str = None) -> int:
        """Get the number of active connections."""
        if session_id:
            return len(self.active_connections.get(session_id, []))
        return sum(len(conns) for conns in self.active_connections.values())


# Singleton
manager = ConnectionManager()




async def _handle_pipeline_start(session_id: str, command_data: dict):
    """Handle START_PIPELINE command: trigger modular Multi-Agent System."""
    from app.agent.core.orchestrator import DSOrchestrator, create_initial_state
    
    filename = command_data.get("file", "dataset.csv")
    
    # Store context for this session
    manager.set_context(session_id, "current_file", filename)
    manager.set_context(session_id, "pipeline_active", True)

    async def orchestrator_callback(msg: dict):
        """Callback to pipe orchestrator events to WebSocket."""
        await manager.send_to_session(session_id, msg)

    try:
        orchestrator = DSOrchestrator(message_callback=orchestrator_callback)
        
        # Check if state already exists in long-term memory for auto-resume
        existing_state_model = memory.get_pipeline_state(session_id)
        if existing_state_model:
            logger.info(f"[WS] Resuming existing pipeline for session: {session_id}")
            await orchestrator.run(existing_state_model.model_dump())
            return

        # Build initial state for a fresh run
        initial_state = create_initial_state(
            session_id=session_id,
            dataset_path=filename,
            user_settings={
                "llm_provider": llm_router.current_provider,
                "model_name": llm_router.current_model
            }
        )

        # Run the autonomous graph
        await orchestrator.run(initial_state)

    except Exception as exc:
        logger.error("[WS] Orchestrator error: %s", exc, exc_info=True)
        await manager.send_to_session(session_id, {
            "type": "error",
            "agent": "system",
            "content": f"⚠️ Pipeline execution error: {str(exc)}"
        })


async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint handler.
    Mounted at: ws://localhost:8000/ws/{session_id}
    """
    await manager.connect(websocket, session_id)

    try:
        while True:
            # Receive messages from client
            raw_data = await websocket.receive_json()
            try:
                incoming = WSClientMessage.model_validate(raw_data)
            except ValidationError as exc:
                await manager.send_to_session(session_id, {
                    "type": "error",
                    "agent": "system",
                    "content": f"Invalid websocket payload: {exc.errors()}",
                })
                continue

            msg_type = incoming.type.value
            content = incoming.content

            if msg_type == "chat":
                # Handle chat message
                memory.save_message(
                    session_id=session_id,
                    role="user",
                    content=content,
                )

                # Get LLM response with context-aware system prompt
                from langchain_core.messages import HumanMessage, SystemMessage

                try:
                    model = llm_router.get_model(task_type="general", streaming=True)

                    # Build context-aware prompt
                    ctx = manager.get_context(session_id)
                    current_file = ctx.get("current_file")
                    system_prompt = _build_system_prompt(current_file)

                    messages = [
                        SystemMessage(content=system_prompt),
                        HumanMessage(content=content),
                    ]

                    # Stream response
                    full_response = ""
                    async for chunk in model.astream(messages):
                        if chunk.content:
                            full_response += chunk.content
                            await manager.send_to_session(session_id, {
                                "type": "status",
                                "agent": "assistant",
                                "content": chunk.content,
                                "metadata": {"streaming": True},
                            })

                    # Save complete response
                    memory.save_message(
                        session_id=session_id,
                        role="assistant",
                        content=full_response,
                    )

                    # Extract mixed cells and emit as notebook cells
                    stage = ctx.get("pipeline_stage", "")
                    await _emit_notebook_cells(session_id, full_response, stage=stage)

                    # Detect completed stages and mark pipeline steps green
                    if ctx.get("pipeline_active"):
                        await _emit_step_completions(session_id, full_response, stage)

                    # Send completion marker
                    await manager.send_to_session(session_id, {
                        "type": "status",
                        "agent": "assistant",
                        "content": full_response,
                        "metadata": {"streaming": False, "complete": True},
                    })

                except Exception as llm_exc:  # noqa: BLE001
                    logger.error("[WS] LLM error during chat: %s", llm_exc, exc_info=True)
                    await manager.send_to_session(session_id, {
                        "type": "error",
                        "agent": "assistant",
                        "content": (
                            f"⚠️ LLM error: {llm_exc}. "
                            "Check Settings → verify your provider URL and model name."
                        ),
                    })

            elif msg_type == "command":
                # Parse command content — could be JSON or plain text
                command_data = {}
                try:
                    command_data = json.loads(content)
                except (json.JSONDecodeError, TypeError):
                    command_data = {"command": content}

                command_name = command_data.get("command", "").upper()

                if command_name == "START_PIPELINE":
                    await _handle_pipeline_start(session_id, command_data)
                else:
                    # Generic command acknowledgment
                    await manager.send_to_session(session_id, {
                        "type": "log",
                        "agent": "system",
                        "content": f"Command received: {content}",
                    })

    except WebSocketDisconnect:
        manager.disconnect(websocket, session_id)
    except Exception as e:
        logger.error(f"[WS] Error: {e}")
        manager.disconnect(websocket, session_id)
