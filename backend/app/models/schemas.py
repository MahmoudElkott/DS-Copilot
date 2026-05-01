# backend/app/models/schemas.py
"""
Pydantic request/response models for the API.
"""
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


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
    TERMINAL = "terminal"
    ERROR = "error"
    RESULT = "result"
    FILE = "file"
    AGENT_ACTION = "agent_action"
    NOTEBOOK_CELL = "notebook_cell"
    DELTA = "delta"
    PROGRESS = "progress"


class WSClientMessageType(str, Enum):
    CHAT = "chat"
    COMMAND = "command"


# ══════════════════════════════════════════════════════════════
# Base
# ══════════════════════════════════════════════════════════════

class StrictModel(BaseModel):
    """Base model with strict-ish validation and forbidden extra keys."""

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
        str_strip_whitespace=True,
    )


# ══════════════════════════════════════════════════════════════
# Notebook / Agent State
# ══════════════════════════════════════════════════════════════

class NotebookCellMetadata(StrictModel):
    id: Optional[str] = None
    language: str = "python"


class NotebookCell(BaseModel):
    model_config = ConfigDict(extra="ignore", validate_assignment=True)
    cell_type: Literal["markdown", "code"]
    metadata: NotebookCellMetadata = Field(default_factory=NotebookCellMetadata)
    source: List[str] = Field(default_factory=list)
    outputs: Optional[List[Any]] = None
    execution_count: Optional[int] = None

    @field_validator("source", mode="before")
    @classmethod
    def normalize_source(cls, value: Any) -> List[str]:
        if isinstance(value, str):
            return value.splitlines()
        if isinstance(value, list):
            return [str(line) for line in value]
        return []


class NotebookDocument(StrictModel):
    cells: List[NotebookCell] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class PipelineErrorInfo(StrictModel):
    step: str
    error: str


class AgentStateModel(StrictModel):
    """Strict validation model for LangGraph shared state."""

    # Session
    session_id: str
    project_name: str = "ds-project"
    project_dir: str = ""

    # Messages
    messages: List[Any] = Field(default_factory=list)

    # User Config
    user_settings: Dict[str, Any] = Field(default_factory=dict)

    # Dataset Info
    dataset_path: str
    dataset_info: Dict[str, Any] = Field(default_factory=dict)

    # Pipeline Results
    cleaning_result: Dict[str, Any] = Field(default_factory=dict)
    eda_result: Dict[str, Any] = Field(default_factory=dict)
    feature_engineering_result: Dict[str, Any] = Field(default_factory=dict)
    model_selection_result: Dict[str, Any] = Field(default_factory=dict)
    training_result: Dict[str, Any] = Field(default_factory=dict)
    testing_result: Dict[str, Any] = Field(default_factory=dict)
    optimization_result: Dict[str, Any] = Field(default_factory=dict)
    execution_result: Dict[str, Any] = Field(default_factory=dict)

    # Code Store
    generated_code: Dict[str, str] = Field(default_factory=dict)
    generated_notebooks: Dict[str, NotebookDocument] = Field(default_factory=dict)

    # Pipeline Control
    current_step: str = "init"
    steps_completed: List[str] = Field(default_factory=list)
    errors: List[PipelineErrorInfo] = Field(default_factory=list)
    should_do_eda: bool = True
    should_compare_models: bool = True

    # Retry / self-healing
    retry_count: int = Field(default=0, ge=0)
    max_retries: int = Field(default=3, ge=0, le=10)
    last_execution_error: Optional[str] = None

    # Harness
    harness_reports: List[Dict[str, Any]] = Field(default_factory=list)

    # Visualization / output
    visualization_payload: Dict[str, Any] = Field(default_factory=dict)
    final_report: Dict[str, Any] = Field(default_factory=dict)


class CodeCellModel(StrictModel):
    id: str
    type: str = "code"
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


from langchain_core.messages import BaseMessage
import operator
from typing import Annotated, Sequence

from pydantic import BaseModel, ConfigDict, Field, field_validator, RootModel

class InternalPipelineModel(StrictModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    session_id: str = ""
    project_name: str = ""
    project_dir: str = ""

    messages: Annotated[Sequence[BaseMessage], operator.add] = Field(default_factory=list)
    user_settings: Dict[str, Any] = Field(default_factory=dict)

    dataset_path: str = ""
    dataset_info: Dict[str, Any] = Field(default_factory=dict)

    cleaning_result: Dict[str, Any] = Field(default_factory=dict)
    eda_result: Dict[str, Any] = Field(default_factory=dict)
    feature_engineering_result: Dict[str, Any] = Field(default_factory=dict)
    model_selection_result: Dict[str, Any] = Field(default_factory=dict)
    training_result: Dict[str, Any] = Field(default_factory=dict)
    testing_result: Dict[str, Any] = Field(default_factory=dict)
    optimization_result: Dict[str, Any] = Field(default_factory=dict)
    execution_result: Dict[str, Any] = Field(default_factory=dict)

    generated_code: Dict[str, str] = Field(default_factory=dict)
    code_out: List[CodeCellModel] = Field(default_factory=list)
    generated_notebooks: Dict[str, Dict[str, Any]] = Field(default_factory=dict)

    current_step: str = ""
    steps_completed: list[str] = Field(default_factory=list)
    errors: list[Dict[str, str]] = Field(default_factory=list)
    should_do_eda: bool = True
    should_compare_models: bool = True

    retry_count: int = 0
    max_retries: int = 3
    last_execution_error: str = ""

    critic_result: Dict[str, Any] = Field(default_factory=dict)
    critic_retry_count: int = 0

    variable_schema: Dict[str, Any] = Field(default_factory=dict)

    harness_reports: list = Field(default_factory=list)
    visualization_payload: Dict[str, Any] = Field(default_factory=dict)
    final_report: Dict[str, Any] = Field(default_factory=dict)


class V1AgentResponseDTO(StrictModel):
    """Decoupled DTO for UI to consume agent state over WebSockets without entire internal structure."""
    session_id: str
    current_step: str
    steps_completed: List[str] = Field(default_factory=list)
    dataset_info: Dict[str, Any] = Field(default_factory=dict)
    visualization_payload: Dict[str, Any] = Field(default_factory=dict)
    errors: List[PipelineErrorInfo] = Field(default_factory=list)
    code_cells: List[CodeCellModel] = Field(default_factory=list)

    @classmethod
    def from_state(cls, state: dict) -> "V1AgentResponseDTO":
        code_out_data = state.get("code_out", [])
        cells = []
        for c in code_out_data:
            if isinstance(c, CodeCellModel):
                cells.append(c)
            elif isinstance(c, dict):
                cells.append(CodeCellModel.model_validate(c))
                
        return cls.model_validate({
            "session_id": state.get("session_id", ""),
            "current_step": state.get("current_step", ""),
            "steps_completed": state.get("steps_completed", []),
            "dataset_info": state.get("dataset_info", {}),
            "visualization_payload": state.get("visualization_payload", {}),
            "errors": state.get("errors", []),
            "code_cells": cells,
        })

# ══════════════════════════════════════════════════════════════
# Chat
# ══════════════════════════════════════════════════════════════

class ChatMessage(StrictModel):
    content: str
    session_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class ChatResponse(StrictModel):
    id: str
    role: str
    content: str
    agent_name: Optional[str] = None
    timestamp: str
    metadata: Optional[Dict[str, Any]] = None


# ══════════════════════════════════════════════════════════════
# Pipeline
# ══════════════════════════════════════════════════════════════

class PipelineConfig(StrictModel):
    dataset_path: str
    project_name: str = "ds-project"
    session_id: Optional[str] = None
    user_settings: Optional[Dict[str, Any]] = None
    execution_env: Literal["local", "e2b"] = "local"
    llm_provider: Optional[str] = None
    model_name: Optional[str] = None
    llm_base_url: Optional[str] = None
    llm_api_key: Optional[str] = None
    e2b_api_key: Optional[str] = None
    python_interpreter: Optional[str] = None
    skip_eda: bool = False
    target_column: Optional[str] = None


class NotebookRunRequest(StrictModel):
    step_key: str = "code_writing"
    timeout: Optional[int] = None


class NotebookRunResponse(StrictModel):
    session_id: str
    step_key: str
    success: bool
    exit_code: Optional[int] = None
    stdout: str = ""
    stderr: str = ""
    execution_time: float = 0.0
    files_created: List[str] = Field(default_factory=list)


class PipelineStepInfo(StrictModel):
    key: str = ""
    name: str
    status: PipelineStepStatus = PipelineStepStatus.PENDING
    agent: str = ""
    execution_time: float = 0.0
    error: Optional[str] = None
    retries: int = 0


class PipelineStatus(StrictModel):
    session_id: str
    status: Literal["running", "completed", "failed"]
    current_step: str
    steps: List[PipelineStepInfo]
    progress_percent: float = 0.0
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


# ══════════════════════════════════════════════════════════════
# Sessions
# ══════════════════════════════════════════════════════════════

class SessionCreate(StrictModel):
    project_name: str = "ds-project"


class SessionInfo(StrictModel):
    session_id: str
    project_name: str
    created_at: str
    status: str = "active"
    steps_completed: int = 0
    total_steps: int = 8


# ══════════════════════════════════════════════════════════════
# WebSocket Messages
# ══════════════════════════════════════════════════════════════

class WSServerMessage(StrictModel):
    """Server → Client WebSocket message."""
    type: WSMessageType
    agent: Optional[str] = None
    content: str = ""
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class WSClientMessage(StrictModel):
    """Client → Server WebSocket message."""
    type: WSClientMessageType
    content: str
    session_id: Optional[str] = None


# ══════════════════════════════════════════════════════════════
# Files
# ══════════════════════════════════════════════════════════════

class FileUploadResponse(StrictModel):
    filename: str
    filepath: str
    size_bytes: int
    message: str = "File uploaded successfully"


class FileTreeResponse(StrictModel):
    project_name: str
    tree: Dict[str, Any]


# ══════════════════════════════════════════════════════════════
# Settings
# ══════════════════════════════════════════════════════════════

class SettingsUpdate(StrictModel):
    llm_provider: Optional[str] = None
    model_name: Optional[str] = None
    execution_env: Optional[str] = None
    python_interpreter: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    openai_api_key: Optional[str] = None
    openai_api_base: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    google_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None
    ollama_base_url: Optional[str] = None
    e2b_api_key: Optional[str] = None
    fallback_llm_provider: Optional[str] = None
    fallback_model_name: Optional[str] = None


class SettingsResponse(StrictModel):
    llm_provider: str
    model_name: str
    execution_env: str
    python_interpreter: Optional[str] = None
    fallback_llm_provider: str = "openai"
    fallback_model_name: str = "gpt-4o"
    temperature: float
    max_tokens: int
    available_providers: List[str]
    openai_api_base: Optional[str] = None
    ollama_base_url: Optional[str] = None
    openai_api_key_loaded: bool = False
    anthropic_api_key_loaded: bool = False
    gemini_api_key_loaded: bool = False
    e2b_api_key_loaded: bool = False
from enum import Enum

class LocalModelsSource(str, Enum):
    LM_STUDIO = "local"
    OLLAMA = "ollama"

class LocalModelsSourceInfo(StrictModel):
    provider: str
    base_url: str
    success: bool
    model_count: int = 0
    error: Optional[str] = None



class LocalModelsResponse(StrictModel):
    models: List[str] = Field(default_factory=list)
    sources: List[LocalModelsSourceInfo] = Field(default_factory=list)


class PythonInterpreterInfo(StrictModel):
    path: str
    version: str
    is_default: bool = False


class PythonInterpretersResponse(StrictModel):
    interpreters: List[PythonInterpreterInfo] = Field(default_factory=list)


# ══════════════════════════════════════════════════════════════
# Stats
# ══════════════════════════════════════════════════════════════

class StatsResponse(StrictModel):
    total_calls: int
    budget_remaining: int
    available_providers: List[str]
    active_sessions: int = 0


# ══════════════════════════════════════════════════════════════
# Health
# ══════════════════════════════════════════════════════════════

class HealthResponse(StrictModel):
    status: str = "ok"
    app_name: str = "DS-Copilot"
    version: str = "1.0.0"
    debug: bool = True
