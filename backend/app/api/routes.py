# backend/app/api/routes.py
"""
REST API routes for DS-Copilot.
"""
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from typing import Optional
import os
import uuid
import json
import asyncio
import logging

from app.config import settings
from app.core.llm_router import llm_router
from app.core.memory import memory
from app.core.file_manager import FileManager
from app.core.executor import create_executor
from app.agents.orchestrator import create_pipeline, create_initial_state
from app.models.schemas import (
    ChatMessage,
    ChatResponse,
    PipelineConfig,
    PipelineStatus,
    PipelineStepInfo,
    PipelineStepStatus,
    SessionCreate,
    SessionInfo,
    FileUploadResponse,
    FileTreeResponse,
    SettingsUpdate,
    SettingsResponse,
    StatsResponse,
    HealthResponse,
)
from app.api.websocket import manager as ws_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["api"])

# In-memory state for active pipelines
_active_pipelines = {}
_session_metadata = {}


# ══════════════════════════════════════════════════════════════
# Health
# ══════════════════════════════════════════════════════════════

@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="ok",
        app_name=settings.APP_NAME,
        debug=settings.DEBUG,
    )


# ══════════════════════════════════════════════════════════════
# Sessions
# ══════════════════════════════════════════════════════════════

@router.post("/sessions", response_model=SessionInfo)
async def create_session(body: SessionCreate):
    """Create a new session."""
    session_id = str(uuid.uuid4())
    from datetime import datetime

    _session_metadata[session_id] = {
        "project_name": body.project_name,
        "created_at": datetime.utcnow().isoformat(),
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
        created_at=_session_metadata[session_id]["created_at"],
    )


@router.get("/sessions", response_model=list[SessionInfo])
async def list_sessions():
    """List all sessions."""
    sessions = []
    all_session_ids = memory.get_all_sessions()

    for sid in all_session_ids:
        meta = _session_metadata.get(sid, {})
        history = memory.get_project_history(sid)
        sessions.append(SessionInfo(
            session_id=sid,
            project_name=meta.get("project_name", "Unknown"),
            created_at=meta.get("created_at", ""),
            status=meta.get("status", "active"),
            steps_completed=len(history),
        ))

    return sessions


@router.get("/sessions/{session_id}")
async def get_session(session_id: str):
    """Get session details with conversation history."""
    conversation = memory.get_conversation(session_id)
    project_history = memory.get_project_history(session_id)
    meta = _session_metadata.get(session_id, {})

    return {
        "session_id": session_id,
        "project_name": meta.get("project_name", "Unknown"),
        "status": meta.get("status", "active"),
        "conversation": conversation,
        "project_history": project_history,
    }


# ══════════════════════════════════════════════════════════════
# File Upload
# ══════════════════════════════════════════════════════════════

@router.post("/upload", response_model=FileUploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    session_id: Optional[str] = None,
):
    """Upload a dataset file."""
    # Validate file extension
    allowed_extensions = {".csv", ".xlsx", ".xls", ".json"}
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {ext}. Allowed: {allowed_extensions}",
        )

    # Read content
    content = await file.read()

    # Validate size (100MB max)
    max_size = 100 * 1024 * 1024  # 100MB
    if len(content) > max_size:
        raise HTTPException(
            status_code=400,
            detail=f"File too large: {len(content) / 1024 / 1024:.1f}MB. Max: 100MB",
        )

    # Save to sandbox directory directly (no executor/venv needed for file saving)
    sandbox_dir = os.path.abspath(settings.LOCAL_SANDBOX_DIR)
    os.makedirs(sandbox_dir, exist_ok=True)
    filepath = os.path.join(sandbox_dir, file.filename)
    with open(filepath, "wb") as f:
        f.write(content)

    logger.info(f"[Upload] File saved: {filepath} ({len(content)} bytes)")

    return FileUploadResponse(
        filename=file.filename,
        filepath=filepath,
        size_bytes=len(content),
    )


# ══════════════════════════════════════════════════════════════
# Pipeline
# ══════════════════════════════════════════════════════════════

@router.post("/pipeline/start")
async def start_pipeline(
    config: PipelineConfig,
    background_tasks: BackgroundTasks,
):
    """Start the full DS pipeline."""
    session_id = str(uuid.uuid4())

    # Store session metadata
    from datetime import datetime
    _session_metadata[session_id] = {
        "project_name": config.project_name,
        "created_at": datetime.utcnow().isoformat(),
        "status": "running",
    }

    # Create initial state
    user_settings = {
        "execution_env": config.execution_env,
    }
    if config.llm_provider:
        user_settings["llm_provider"] = config.llm_provider

    initial_state = create_initial_state(
        session_id=session_id,
        dataset_path=config.dataset_path,
        project_name=config.project_name,
        user_settings=user_settings,
    )

    if not config.skip_eda:
        initial_state["should_do_eda"] = True
    else:
        initial_state["should_do_eda"] = False

    # Store reference
    _active_pipelines[session_id] = {
        "state": initial_state,
        "status": "running",
        "config": config.model_dump(),
    }

    # Run pipeline in background
    background_tasks.add_task(_run_pipeline, session_id, initial_state)

    return {
        "session_id": session_id,
        "status": "started",
        "message": f"Pipeline started for {config.project_name}",
    }


async def _run_pipeline(session_id: str, initial_state: dict):
    """Run the pipeline in the background and send updates via WebSocket."""
    try:
        pipeline = create_pipeline()

        # Track steps for WebSocket updates
        step_order = [
            "data_ingest", "data_cleaning", "eda",
            "model_selection", "code_writer", "testing",
            "optimization", "documentation",
        ]

        # Send start event
        await ws_manager.send_to_session(session_id, {
            "type": "status",
            "agent": "orchestrator",
            "content": "Pipeline started",
            "metadata": {"step": "start", "total_steps": len(step_order)},
        })

        # Run the pipeline
        final_state = None
        async for event in pipeline.astream(initial_state):
            # event is a dict with node_name -> output
            for node_name, output in event.items():
                logger.info(f"[Pipeline] Step completed: {node_name}")

                # Send WebSocket update
                await ws_manager.send_to_session(session_id, {
                    "type": "status",
                    "agent": node_name,
                    "content": f"Step completed: {node_name}",
                    "metadata": {
                        "step": node_name,
                        "steps_completed": output.get("steps_completed", []),
                    },
                })

                # Send code if generated
                generated_code = output.get("generated_code", {})
                for step_name, code in generated_code.items():
                    if code and step_name == node_name.replace("_node", ""):
                        await ws_manager.send_to_session(session_id, {
                            "type": "code",
                            "agent": node_name,
                            "content": code,
                            "metadata": {"step": step_name},
                        })

                # Send messages
                for msg in output.get("messages", []):
                    await ws_manager.send_to_session(session_id, {
                        "type": "log",
                        "agent": node_name,
                        "content": msg.content,
                    })

                final_state = output

        # Pipeline complete
        _active_pipelines[session_id]["status"] = "completed"
        _active_pipelines[session_id]["final_state"] = final_state
        _session_metadata[session_id]["status"] = "completed"

        await ws_manager.send_to_session(session_id, {
            "type": "result",
            "agent": "orchestrator",
            "content": "Pipeline completed successfully!",
            "metadata": final_state.get("final_report", {}),
        })

    except Exception as e:
        logger.error(f"[Pipeline] Failed: {e}", exc_info=True)
        _active_pipelines[session_id]["status"] = "failed"
        _session_metadata[session_id]["status"] = "failed"

        await ws_manager.send_to_session(session_id, {
            "type": "error",
            "agent": "orchestrator",
            "content": f"Pipeline failed: {str(e)}",
        })


@router.get("/pipeline/status/{session_id}", response_model=PipelineStatus)
async def get_pipeline_status(session_id: str):
    """Get pipeline status."""
    pipeline_data = _active_pipelines.get(session_id)
    if not pipeline_data:
        raise HTTPException(status_code=404, detail="Pipeline not found")

    state = pipeline_data.get("final_state") or pipeline_data.get("state", {})
    steps_completed = state.get("steps_completed", [])

    step_names = [
        ("data_ingest", "Data Ingestion", "DataIngestAgent"),
        ("data_cleaning", "Data Cleaning", "DataCleaningAgent"),
        ("eda", "EDA", "EDAAgent"),
        ("model_selection", "Model Selection", "ModelSelectionAgent"),
        ("code_writing", "Code Writing", "CodeWriterAgent"),
        ("testing", "Testing", "TestingAgent"),
        ("optimization", "Optimization", "OptimizationAgent"),
        ("documentation", "Documentation", "DocumentationAgent"),
    ]

    steps = []
    for key, name, agent in step_names:
        if key in steps_completed:
            status = PipelineStepStatus.COMPLETED
        elif state.get("current_step", "").startswith(key):
            status = PipelineStepStatus.RUNNING
        else:
            status = PipelineStepStatus.PENDING

        steps.append(PipelineStepInfo(
            name=name,
            status=status,
            agent=agent,
        ))

    progress = len(steps_completed) / len(step_names) * 100

    return PipelineStatus(
        session_id=session_id,
        status=pipeline_data["status"],
        current_step=state.get("current_step", "unknown"),
        steps=steps,
        progress_percent=round(progress, 1),
    )


# ══════════════════════════════════════════════════════════════
# Chat
# ══════════════════════════════════════════════════════════════

@router.post("/chat", response_model=ChatResponse)
async def chat(message: ChatMessage):
    """Send a chat message and get a response."""
    session_id = message.session_id or str(uuid.uuid4())

    # Save user message
    memory.save_message(
        session_id=session_id,
        role="user",
        content=message.content,
    )

    # Get LLM response
    from langchain_core.messages import HumanMessage, SystemMessage

    model = llm_router.get_model(task_type="general")

    # Build conversation context
    history = memory.get_conversation(session_id, limit=20)
    messages = [
        SystemMessage(content=(
            "You are DS-Copilot, an expert data science assistant. "
            "Help users with ML pipeline questions, data analysis, and code. "
            "Be concise and helpful."
        )),
    ]
    for msg in history:
        if msg["role"] == "user":
            messages.append(HumanMessage(content=msg["content"]))

    messages.append(HumanMessage(content=message.content))

    response = await model.ainvoke(messages)

    # Save assistant response
    from datetime import datetime
    msg_id = memory.save_message(
        session_id=session_id,
        role="assistant",
        content=response.content,
    )

    return ChatResponse(
        id=msg_id,
        role="assistant",
        content=response.content,
        timestamp=datetime.utcnow().isoformat(),
    )


@router.get("/chat/{session_id}", response_model=list[ChatResponse])
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


# ══════════════════════════════════════════════════════════════
# Files
# ══════════════════════════════════════════════════════════════

@router.get("/files/{session_id}", response_model=FileTreeResponse)
async def get_file_tree(session_id: str):
    """Get the project file tree."""
    pipeline_data = _active_pipelines.get(session_id, {})
    state = pipeline_data.get("final_state") or pipeline_data.get("state", {})
    project_dir = state.get("project_dir", "")

    if not project_dir or not os.path.exists(project_dir):
        return FileTreeResponse(
            project_name=state.get("project_name", "unknown"),
            tree={},
        )

    file_manager = FileManager()
    tree = file_manager.get_file_tree(project_dir)

    return FileTreeResponse(
        project_name=state.get("project_name", "unknown"),
        tree=tree,
    )


@router.get("/files/{session_id}/download/{filepath:path}")
async def download_file(session_id: str, filepath: str):
    """Download a file from the project."""
    from fastapi.responses import FileResponse

    pipeline_data = _active_pipelines.get(session_id, {})
    state = pipeline_data.get("final_state") or pipeline_data.get("state", {})
    project_dir = state.get("project_dir", "")

    full_path = os.path.join(project_dir, filepath)
    if not os.path.exists(full_path):
        raise HTTPException(status_code=404, detail="File not found")

    # Security: ensure path is within project dir
    if not os.path.abspath(full_path).startswith(os.path.abspath(project_dir)):
        raise HTTPException(status_code=403, detail="Access denied")

    return FileResponse(full_path)


# ══════════════════════════════════════════════════════════════
# Settings
# ══════════════════════════════════════════════════════════════

@router.get("/settings", response_model=SettingsResponse)
async def get_settings():
    """Get current settings."""
    return SettingsResponse(
        llm_provider=settings.DEFAULT_LLM_PROVIDER.value,
        model_name=settings.DEFAULT_MODEL,
        execution_env=settings.DEFAULT_EXECUTION_ENV.value,
        temperature=settings.DEFAULT_TEMPERATURE,
        max_tokens=settings.DEFAULT_MAX_TOKENS,
        available_providers=[p.value for p in llm_router._available_providers],
    )


@router.put("/settings", response_model=SettingsResponse)
async def update_settings(update: SettingsUpdate):
    """Update runtime settings."""
    # Update settings in memory (runtime only — not persisted to .env)
    if update.llm_provider:
        settings.DEFAULT_LLM_PROVIDER = update.llm_provider
    if update.model_name:
        settings.DEFAULT_MODEL = update.model_name
    if update.execution_env:
        settings.DEFAULT_EXECUTION_ENV = update.execution_env
    if update.temperature is not None:
        settings.DEFAULT_TEMPERATURE = update.temperature
    if update.max_tokens is not None:
        settings.DEFAULT_MAX_TOKENS = update.max_tokens
    if update.openai_api_key:
        settings.OPENAI_API_KEY = update.openai_api_key
    if update.anthropic_api_key:
        settings.ANTHROPIC_API_KEY = update.anthropic_api_key
    if update.google_api_key:
        settings.GOOGLE_API_KEY = update.google_api_key
    if update.ollama_base_url:
        settings.OLLAMA_BASE_URL = update.ollama_base_url
    if update.e2b_api_key:
        settings.E2B_API_KEY = update.e2b_api_key

    # Re-detect providers after key update
    llm_router._available_providers = llm_router._detect_available_providers()

    return await get_settings()


# ══════════════════════════════════════════════════════════════
# Stats
# ══════════════════════════════════════════════════════════════

@router.get("/stats", response_model=StatsResponse)
async def get_stats():
    """Get LLM usage stats."""
    stats = llm_router.get_stats()
    return StatsResponse(
        total_calls=stats["total_calls"],
        budget_remaining=stats["budget_remaining"],
        available_providers=stats["available_providers"],
        active_sessions=len(_active_pipelines),
    )
