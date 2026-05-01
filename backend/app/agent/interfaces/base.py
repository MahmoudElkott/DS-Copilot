from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import BaseModel

class ToolResult(BaseModel):
    output: str
    error: Optional[str] = None
    artifacts: Dict[str, Any] = {}

class BaseTool(ABC):
    @abstractmethod
    async def run(self, **kwargs) -> ToolResult:
        pass

class BaseAgent(ABC):
    @abstractmethod
    async def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        pass

class BaseLLMProvider(ABC):
    @abstractmethod
    async def generate(self, messages: List[Dict[str, str]], **kwargs) -> str:
        pass
    
    @abstractmethod
    async def is_healthy(self) -> bool:
        pass
