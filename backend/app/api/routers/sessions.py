# backend/app/api/routers/sessions.py
import uuid
import logging
from datetime import datetime, timezone
from fastapi import APIRouter
from app.infrastructure.memory import memory
from app.api.state import session_metadata
from app.models.schemas import SessionCreate, SessionInfo

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sessions", tags=["sessions"])

@router.post("", response_model=SessionInfo)
async def create_session(body: SessionCreate):
    """Create a new session."""
    session_id = str(uuid.uuid4())

    session_metadata[session_id] = {
        "project_name": body.project_name,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "active",
    }

    memory.save_message(
        session_id=session_id,
        role="system",
        content=f"Session created for project: {body.project_name}",
    )

    return SessionInfo(
        session_id=session_id,
        project_name=body.project_name,
        created_at=session_metadata[session_id]["created_at"],
    )

@router.get("", response_model=list[SessionInfo])
async def list_sessions():
    """List all sessions."""
    sessions = []
    all_session_ids = memory.get_all_sessions()

    for sid in all_session_ids:
        meta = session_metadata.get(sid, {})
        history = memory.get_project_history(sid)
        sessions.append(
            SessionInfo(
                session_id=sid,
                project_name=meta.get("project_name", "Unknown"),
                created_at=meta.get("created_at", ""),
                status=meta.get("status", "active"),
                steps_completed=len(history),
            )
        )

    return sessions

@router.get("/{session_id}")
async def get_session(session_id: str):
    """Get session details."""
    conversation = memory.get_conversation(session_id)
    project_history = memory.get_project_history(session_id)
    meta = session_metadata.get(session_id, {})

    return {
        "session_id": session_id,
        "project_name": meta.get("project_name", "Unknown"),
        "status": meta.get("status", "active"),
        "conversation": conversation,
        "project_history": project_history,
    }
