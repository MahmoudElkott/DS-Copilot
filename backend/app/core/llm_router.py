# backend/app/core/llm_router.py
from typing import Optional, Dict, Any, AsyncGenerator
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.chat_models import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.language_models import BaseChatModel
from app.config import settings, LLMProvider
import tiktoken
import logging

logger = logging.getLogger(__name__)


class LLMRouter:
    """
    Intelligent LLM Router that selects the best model
    based on task type, cost, and performance.
    """

    PROVIDER_MODELS = {
        LLMProvider.OPENAI: {
            "default": "gpt-4o",
            "fast": "gpt-4o-mini",
            "powerful": "gpt-4o",
            "code": "gpt-4o",
        },
        LLMProvider.ANTHROPIC: {
            "default": "claude-sonnet-4-20250514",
            "fast": "claude-haiku-4-20250514",
            "powerful": "claude-sonnet-4-20250514",
            "code": "claude-sonnet-4-20250514",
        },
        LLMProvider.GOOGLE: {
            "default": "gemini-2.0-flash",
            "fast": "gemini-2.0-flash",
            "powerful": "gemini-2.5-pro-preview-06-05",
            "code": "gemini-2.5-pro-preview-06-05",
        },
        LLMProvider.OLLAMA: {
            "default": "llama3.1",
            "fast": "llama3.1",
            "powerful": "llama3.1:70b",
            "code": "codellama",
        },
    }

    # Task-to-provider routing strategy
    TASK_ROUTING = {
        "data_cleaning": {"provider": LLMProvider.OPENAI, "tier": "fast"},
        "eda": {"provider": LLMProvider.OPENAI, "tier": "default"},
        "model_selection": {"provider": LLMProvider.ANTHROPIC, "tier": "powerful"},
        "code_writing": {"provider": LLMProvider.ANTHROPIC, "tier": "code"},
        "testing": {"provider": LLMProvider.OPENAI, "tier": "fast"},
        "documentation": {"provider": LLMProvider.OPENAI, "tier": "fast"},
        "optimization": {"provider": LLMProvider.ANTHROPIC, "tier": "powerful"},
        "general": {"provider": LLMProvider.OPENAI, "tier": "default"},
    }

    def __init__(self):
        self._models_cache: Dict[str, BaseChatModel] = {}
        self._call_count = 0
        self._total_tokens = 0
        self._available_providers = self._detect_available_providers()

    def _detect_available_providers(self) -> list:
        available = []
        if settings.OPENAI_API_KEY:
            available.append(LLMProvider.OPENAI)
        if settings.ANTHROPIC_API_KEY:
            available.append(LLMProvider.ANTHROPIC)
        if settings.GOOGLE_API_KEY:
            available.append(LLMProvider.GOOGLE)
        # Ollama is always potentially available locally
        available.append(LLMProvider.OLLAMA)
        logger.info(f"Available LLM providers: {available}")
        return available

    def _create_model(
        self,
        provider: LLMProvider,
        model_name: str,
        temperature: float = 0.1,
        max_tokens: int = 4096,
        streaming: bool = False,
    ) -> BaseChatModel:
        cache_key = f"{provider}:{model_name}:{temperature}:{streaming}"
        if cache_key in self._models_cache:
            return self._models_cache[cache_key]

        if provider == LLMProvider.OPENAI:
            kwargs = dict(
                model=model_name,
                temperature=temperature,
                max_tokens=max_tokens,
                streaming=streaming,
                api_key=settings.OPENAI_API_KEY,
            )
            if settings.OPENAI_API_BASE:
                kwargs["base_url"] = settings.OPENAI_API_BASE
            model = ChatOpenAI(**kwargs)
        elif provider == LLMProvider.ANTHROPIC:
            model = ChatAnthropic(
                model=model_name,
                temperature=temperature,
                max_tokens=max_tokens,
                streaming=streaming,
                api_key=settings.ANTHROPIC_API_KEY,
            )
        elif provider == LLMProvider.GOOGLE:
            model = ChatGoogleGenerativeAI(
                model=model_name,
                temperature=temperature,
                max_output_tokens=max_tokens,
                google_api_key=settings.GOOGLE_API_KEY,
            )
        elif provider == LLMProvider.OLLAMA:
            model = ChatOllama(
                model=model_name,
                temperature=temperature,
                base_url=settings.OLLAMA_BASE_URL,
            )
        else:
            raise ValueError(f"Unknown provider: {provider}")

        self._models_cache[cache_key] = model
        return model

    def get_model(
        self,
        task_type: str = "general",
        provider_override: Optional[LLMProvider] = None,
        model_override: Optional[str] = None,
        temperature: Optional[float] = None,
        streaming: bool = False,
    ) -> BaseChatModel:
        """Get the best model for a specific task."""

        if self._call_count >= settings.API_CALL_BUDGET:
            raise RuntimeError(
                f"API call budget exceeded: {settings.API_CALL_BUDGET}"
            )

        # Determine provider and model
        if provider_override and model_override:
            provider = provider_override
            model_name = model_override
        elif provider_override:
            provider = provider_override
            tier = self.TASK_ROUTING.get(task_type, {}).get("tier", "default")
            model_name = self.PROVIDER_MODELS[provider][tier]
        else:
            routing = self.TASK_ROUTING.get(
                task_type,
                {"provider": settings.DEFAULT_LLM_PROVIDER, "tier": "default"},
            )
            provider = routing["provider"]
            # Fallback if provider not available
            if provider not in self._available_providers:
                provider = self._available_providers[0]
            tier = routing["tier"]
            model_name = self.PROVIDER_MODELS[provider][tier]

        temp = temperature if temperature is not None else settings.DEFAULT_TEMPERATURE

        self._call_count += 1
        logger.info(
            f"[Router] Task: {task_type} → {provider}:{model_name} "
            f"(call #{self._call_count})"
        )

        return self._create_model(
            provider=provider,
            model_name=model_name,
            temperature=temp,
            streaming=streaming,
        )

    async def stream_response(
        self, messages: list, task_type: str = "general"
    ) -> AsyncGenerator[str, None]:
        """Stream response tokens."""
        model = self.get_model(task_type=task_type, streaming=True)
        async for chunk in model.astream(messages):
            if chunk.content:
                yield chunk.content

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_calls": self._call_count,
            "budget_remaining": settings.API_CALL_BUDGET - self._call_count,
            "available_providers": [p.value for p in self._available_providers],
        }


# Singleton
llm_router = LLMRouter()
