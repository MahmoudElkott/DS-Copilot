# backend/app/core/executor.py
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from dataclasses import dataclass
import asyncio
import logging

logger = logging.getLogger(__name__)


@dataclass
class ExecutionResult:
    success: bool
    stdout: str
    stderr: str
    return_value: Any = None
    execution_time: float = 0.0
    files_created: list = None

    def __post_init__(self):
        if self.files_created is None:
            self.files_created = []


class BaseExecutor(ABC):
    @abstractmethod
    async def execute(self, code: str, timeout: int = 60) -> ExecutionResult:
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


def create_executor(env_type: str = "local") -> BaseExecutor:
    """Factory function to create the appropriate executor."""
    from app.config import settings

    if env_type == "e2b":
        if not settings.E2B_API_KEY:
            raise ValueError("E2B_API_KEY not configured")
        from app.core.e2b_executor import E2BExecutor
        return E2BExecutor(api_key=settings.E2B_API_KEY)

    from app.core.local_executor import LocalExecutor
    return LocalExecutor(sandbox_dir=settings.LOCAL_SANDBOX_DIR)
