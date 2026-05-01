from typing import List, Dict, Any, Optional
from langchain_openai import ChatOpenAI
from app.agent.interfaces.base import BaseLLMProvider
import httpx

class OpenAIProvider(BaseLLMProvider):
    def __init__(self, model_name: str, api_key: str, base_url: Optional[str] = None, **kwargs):
        self.model = ChatOpenAI(model=model_name, api_key=api_key, base_url=base_url, **kwargs)
        self.base_url = base_url

    async def generate(self, messages: List[Dict[str, str]], **kwargs) -> str:
        response = await self.model.ainvoke(messages, **kwargs)
        return response.content

    async def is_healthy(self) -> bool:
        if not self.base_url:
            return True # Assume OpenAI Cloud is up if key is valid
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                res = await client.get(f"{self.base_url.rstrip('/')}/models")
                return res.status_code == 200
        except Exception:
            return False
