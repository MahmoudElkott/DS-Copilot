# backend/app/models/schemas.py
"""
Pydantic request/response models for the API.
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum


# ══════════════════════════════════════════════════════════════
# Enums
# ══════════════════════════════════════════════════════════════

class PipelineStepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class WSMessageType(str, Enum):
    STATUS = "status"
    CODE = "code"
    LOG = "log"
    ERROR = "error"
    RESULT = "result"
    FILE = "file"


class WSClientMessageType(str, Enum):
    CHAT = "chat"
    COMMAND = "command"


# ══════════════════════════════════════════════════════════════
# Chat
# ══════════════════════════════════════════════════════════════

class ChatMessage(BaseModel):
    content: str
    session_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class ChatResponse(BaseModel):
    id: str
    role: str
    content: str
    agent_name: Optional[str] = None
    timestamp: str
    metadata: Optional[Dict[str, Any]] = None


# ══════════════════════════════════════════════════════════════
# Pipeline
# ══════════════════════════════════════════════════════════════

class PipelineConfig(BaseModel):
    dataset_path: str
    project_name: str = "ds-project"
    execution_env: str = "local"
    llm_provider: Optional[str] = None
    skip_eda: bool = False
    target_column: Optional[str] = None


class PipelineStepInfo(BaseModel):
    name: str
    status: PipelineStepStatus = PipelineStepStatus.PENDING
    agent: str = ""
    execution_time: float = 0.0
    error: Optional[str] = None
    retries: int = 0


class PipelineStatus(BaseModel):
    session_id: str
    status: str  # running, completed, failed
    current_step: str
    steps: List[PipelineStepInfo]
    progress_percent: float = 0.0
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


# ══════════════════════════════════════════════════════════════
# Sessions
# ══════════════════════════════════════════════════════════════

class SessionCreate(BaseModel):
    project_name: str = "ds-project"


class SessionInfo(BaseModel):
    session_id: str
    project_name: str
    created_at: str
    status: str = "active"
    steps_completed: int = 0
    total_steps: int = 8


# ══════════════════════════════════════════════════════════════
# WebSocket Messages
# ══════════════════════════════════════════════════════════════

class WSServerMessage(BaseModel):
    """Server → Client WebSocket message."""
    type: WSMessageType
    agent: Optional[str] = None
    content: str = ""
    metadata: Optional[Dict[str, Any]] = None
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class WSClientMessage(BaseModel):
    """Client → Server WebSocket message."""
    type: WSClientMessageType
    content: str
    session_id: Optional[str] = None


# ══════════════════════════════════════════════════════════════
# Files
# ══════════════════════════════════════════════════════════════

class FileUploadResponse(BaseModel):
    filename: str
    filepath: str
    size_bytes: int
    message: str = "File uploaded successfully"


class FileTreeResponse(BaseModel):
    project_name: str
    tree: Dict[str, Any]


# ══════════════════════════════════════════════════════════════
# Settings
# ══════════════════════════════════════════════════════════════

class SettingsUpdate(BaseModel):
    llm_provider: Optional[str] = None
    model_name: Optional[str] = None
    execution_env: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    google_api_key: Optional[str] = None
    ollama_base_url: Optional[str] = None
    e2b_api_key: Optional[str] = None


class SettingsResponse(BaseModel):
    llm_provider: str
    model_name: str
    execution_env: str
    temperature: float
    max_tokens: int
    available_providers: List[str]


# ══════════════════════════════════════════════════════════════
# Stats
# ══════════════════════════════════════════════════════════════

class StatsResponse(BaseModel):
    total_calls: int
    budget_remaining: int
    available_providers: List[str]
    active_sessions: int = 0


# ══════════════════════════════════════════════════════════════
# Health
# ══════════════════════════════════════════════════════════════

class HealthResponse(BaseModel):
    status: str = "ok"
    app_name: str = "DS-Copilot"
    version: str = "1.0.0"
    debug: bool = True
