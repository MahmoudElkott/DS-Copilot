# backend/app/core/executor.py
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Dict, Optional

import logging

logger = logging.getLogger(__name__)


ExecutionStreamHandler = Callable[[str, str], Awaitable[None]]
ExecutionLogSink = Callable[[Dict[str, Any]], Awaitable[None]]

_EXECUTION_LOG_SINKS: Dict[str, ExecutionLogSink] = {}


def register_execution_log_sink(session_id: str, sink: ExecutionLogSink) -> None:
    """Register a per-session sink used for live stdout/stderr forwarding."""
    if session_id:
        _EXECUTION_LOG_SINKS[session_id] = sink


def unregister_execution_log_sink(session_id: str) -> None:
    """Remove a previously registered session sink."""
    _EXECUTION_LOG_SINKS.pop(session_id, None)


async def emit_execution_log(
    session_id: str,
    stream: str,
    content: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    """Emit execution log chunks to a registered sink if present."""
    if not session_id or not content:
        return
    sink = _EXECUTION_LOG_SINKS.get(session_id)
    if sink is None:
        return
    await sink(
        {
            "stream": stream,
            "content": content,
            "metadata": metadata or {},
        }
    )


def resolve_stream_handler(
    session_id: Optional[str],
    explicit_handler: Optional[ExecutionStreamHandler] = None,
) -> Optional[ExecutionStreamHandler]:
    """Resolve explicit stream handler or a session-bound default sink."""
    if explicit_handler is not None:
        return explicit_handler
    if not session_id:
        return None

    async def _session_handler(stream: str, chunk: str) -> None:
        await emit_execution_log(session_id, stream, chunk)

    return _session_handler


@dataclass
class ExecutionResult:
    success: bool
    stdout: str
    stderr: str
    exit_code: Optional[int] = None
    return_value: Any = None
    execution_time: float = 0.0
    files_created: list = None

    def __post_init__(self):
        if self.files_created is None:
            self.files_created = []


class BaseExecutor(ABC):
    @abstractmethod
    async def execute(
        self,
        code: str,
        timeout: int = 120,
        stream_handler: Optional[ExecutionStreamHandler] = None,
        context_config: Optional[Dict[str, str]] = None,
    ) -> ExecutionResult:
        pass

    @abstractmethod
    async def install_package(self, package: str) -> bool:
        pass

    @abstractmethod
    async def upload_file(self, filename: str, content: bytes) -> str:
        pass

    @abstractmethod
    async def download_file(self, filepath: str) -> bytes:
        pass


def create_executor(
    env_type: str = "local",
    *,
    session_id: Optional[str] = None,
    python_interpreter: Optional[str] = None,
    e2b_api_key: Optional[str] = None,
    stream_handler: Optional[ExecutionStreamHandler] = None,
) -> BaseExecutor:
    """Factory function to create the appropriate executor."""
    from app.config import settings

    resolved_handler = resolve_stream_handler(session_id, stream_handler)

    if env_type == "e2b":
        resolved_e2b_api_key = (e2b_api_key or settings.E2B_API_KEY or "").strip()
        if not resolved_e2b_api_key:
            raise ValueError("E2B_API_KEY not configured")
        from app.infrastructure.e2b_executor import E2BExecutor
        return E2BExecutor(
            api_key=resolved_e2b_api_key,
            session_id=session_id,
            stream_handler=resolved_handler,
        )

    if env_type == "docker":
        from app.infrastructure.docker_executor import DockerExecutor
        return DockerExecutor(
            session_id=session_id,
            stream_handler=resolved_handler,
        )

    from app.infrastructure.local_executor import LocalExecutor
    return LocalExecutor(
        sandbox_dir=settings.LOCAL_SANDBOX_DIR,
        python_interpreter=python_interpreter,
        session_id=session_id,
        stream_handler=resolved_handler,
    )
