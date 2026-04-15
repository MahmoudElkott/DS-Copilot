# backend/app/api/websocket.py
"""
WebSocket endpoint for real-time agent updates, code streaming, and pipeline progress.

Protocol:
  Server → Client:
    {"type": "status"|"code"|"log"|"error"|"result"|"file", "agent": "...", "content": "...", "metadata": {}, "timestamp": "ISO8601"}

  Client → Server:
    {"type": "chat"|"command", "content": "...", "session_id": "uuid"}
"""
from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, List, Any
import json
import logging
from datetime import datetime

from app.core.memory import memory
from app.core.llm_router import llm_router

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections per session."""

    def __init__(self):
        # session_id -> list of WebSocket connections
        self.active_connections: Dict[str, List[WebSocket]] = {}

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

    async def send_to_session(self, session_id: str, message: dict):
        """Send a message to all connections in a session."""
        if "timestamp" not in message:
            message["timestamp"] = datetime.utcnow().isoformat()

        connections = self.active_connections.get(session_id, [])
        disconnected = []

        for ws in connections:
            try:
                await self._send_json(ws, message)
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


async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint handler.
    Mounted at: ws://localhost:8000/ws/{session_id}
    """
    await manager.connect(websocket, session_id)

    try:
        while True:
            # Receive messages from client
            data = await websocket.receive_json()

            msg_type = data.get("type", "chat")
            content = data.get("content", "")

            if msg_type == "chat":
                # Handle chat message
                memory.save_message(
                    session_id=session_id,
                    role="user",
                    content=content,
                )

                # Get LLM response
                from langchain_core.messages import HumanMessage, SystemMessage

                model = llm_router.get_model(task_type="general", streaming=True)

                messages = [
                    SystemMessage(content=(
                        "You are DS-Copilot, an expert data science assistant. "
                        "Help users with ML pipeline questions. Be concise."
                    )),
                    HumanMessage(content=content),
                ]

                # Stream response
                full_response = ""
                async for chunk in model.astream(messages):
                    if chunk.content:
                        full_response += chunk.content
                        await manager.send_to_session(session_id, {
                            "type": "code",
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

                # Send completion marker
                await manager.send_to_session(session_id, {
                    "type": "status",
                    "agent": "assistant",
                    "content": full_response,
                    "metadata": {"streaming": False, "complete": True},
                })

            elif msg_type == "command":
                # Handle commands (e.g., stop pipeline, retry step)
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
