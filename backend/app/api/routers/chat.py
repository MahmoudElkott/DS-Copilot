# backend/app/api/routers/chat.py
import logging
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter
from langchain_core.messages import HumanMessage, SystemMessage

from app.infrastructure.llm_router import llm_router
from app.infrastructure.memory import memory
from app.models.schemas import ChatMessage, ChatResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])

@router.post("", response_model=ChatResponse)
async def chat(message: ChatMessage):
    """Send a chat message and get a response."""
    session_id = message.session_id or str(uuid.uuid4())

    memory.save_message(
        session_id=session_id,
        role="user",
        content=message.content,
    )

    model = llm_router.get_model(task_type="general")

    history = memory.get_conversation(session_id, limit=20)
    messages = [
        SystemMessage(
            content=(
                "You are DS-Copilot, an expert data science assistant. "
                "Help users with ML pipeline questions, data analysis, and code. "
                "Be concise and helpful."
            )
        ),
    ]
    for msg in history:
        if msg["role"] == "user":
            messages.append(HumanMessage(content=msg["content"]))

    messages.append(HumanMessage(content=message.content))

    response = await model.ainvoke(messages)

    msg_id = memory.save_message(
        session_id=session_id,
        role="assistant",
        content=response.content,
    )

    return ChatResponse(
        id=msg_id,
        role="assistant",
        content=response.content,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )

@router.get("/{session_id}", response_model=list[ChatResponse])
async def get_chat_history(session_id: str, limit: int = 50):
    """Get chat history for a session."""
    messages = memory.get_conversation(session_id, limit=limit)
    return [
        ChatResponse(
            id=msg["id"],
            role=msg["role"],
            content=msg["content"],
            agent_name=msg.get("agent_name"),
            timestamp=msg["timestamp"],
            metadata=msg.get("metadata"),
        )
        for msg in messages
    ]
