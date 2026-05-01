# backend/app/core/llm_router.py
import asyncio
import httpx
from typing import Optional, Dict, Any, AsyncGenerator, List
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.chat_models import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.language_models import BaseChatModel
from app.config import settings, LLMProvider
from app.models.schemas import LocalModelsSource
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
        LLMProvider.LOCAL: {
            "default": "local-model",
            "fast": "local-model",
            "powerful": "local-model",
            "code": "local-model",
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
        self._local_health_status = True
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._health_check_loop())
        except RuntimeError:
            pass # Loop not running yet, will rely on request_timeout

    async def _health_check_loop(self):
        while True:
            urls_to_check = []
            if settings.LM_STUDIO_BASE_URL:
                urls_to_check.append(settings.LM_STUDIO_BASE_URL)
            else:
                urls_to_check.append("http://localhost:1234/v1")
            if settings.OLLAMA_BASE_URL:
                urls_to_check.append(settings.OLLAMA_BASE_URL)
            
            is_up = False
            for url in urls_to_check:
                try:
                    async with httpx.AsyncClient(timeout=2.0) as client:
                        res = await client.get(f"{url.rstrip('/')}/models")
                        if res.status_code == 200:
                            is_up = True
                            break
                except Exception:
                    pass
            self._local_health_status = is_up
            await asyncio.sleep(10)

    def _detect_available_providers(self) -> list:
        available = []
        if settings.OPENAI_API_KEY or settings.OPENAI_API_BASE:
            available.append(LLMProvider.OPENAI)
        if settings.ANTHROPIC_API_KEY:
            available.append(LLMProvider.ANTHROPIC)
        if settings.GEMINI_API_KEY or settings.GOOGLE_API_KEY:
            available.append(LLMProvider.GOOGLE)
        # Ollama is always potentially available locally
        available.append(LLMProvider.OLLAMA)
        # LOCAL (LM Studio) is always potentially available
        available.append(LLMProvider.LOCAL)
        logger.info(f"Available LLM providers: {available}")
        return available

    def _normalize_provider(self, provider_value: str) -> LLMProvider:
        normalized = (provider_value or "").strip().lower()
        provider_aliases = {
            "gemini": LLMProvider.GOOGLE,
            "google": LLMProvider.GOOGLE,
            "lmstudio": LLMProvider.LOCAL,
            "local": LLMProvider.LOCAL,
            "local-openai": LLMProvider.LOCAL,
        }
        if normalized in provider_aliases:
            return provider_aliases[normalized]
        return LLMProvider(normalized)

    def _provider_available(
        self,
        provider: LLMProvider,
        runtime_settings: Optional[Dict[str, Any]] = None,
    ) -> bool:
        runtime = runtime_settings or {}
        runtime_api_key = (runtime.get("llm_api_key") or "").strip()
        runtime_base_url = (runtime.get("llm_base_url") or "").strip()

        if provider == LLMProvider.OPENAI:
            return bool(
                runtime_api_key
                or settings.OPENAI_API_KEY
                or runtime_base_url
                or settings.OPENAI_API_BASE
            )
        if provider == LLMProvider.ANTHROPIC:
            return bool(runtime_api_key or settings.ANTHROPIC_API_KEY)
        if provider == LLMProvider.GOOGLE:
            return bool(runtime_api_key or settings.GEMINI_API_KEY or settings.GOOGLE_API_KEY)
        if provider == LLMProvider.OLLAMA:
            return bool(runtime_base_url or settings.OLLAMA_BASE_URL)
        if provider == LLMProvider.LOCAL:
            return bool(runtime_base_url or settings.LM_STUDIO_BASE_URL or "http://localhost:1234/v1")
        return False

    def _create_model(
        self,
        provider: LLMProvider,
        model_name: str,
        temperature: float = 0.1,
        max_tokens: int = 4096,
        streaming: bool = False,
        runtime_settings: Optional[Dict[str, Any]] = None,
    ) -> BaseChatModel:
        runtime = runtime_settings or {}
        runtime_base_url = (runtime.get("llm_base_url") or "").strip()
        runtime_api_key = (runtime.get("llm_api_key") or "").strip()
        api_key_signature = str(hash(runtime_api_key)) if runtime_api_key else ""
        cache_key = (
            f"{provider}:{model_name}:{temperature}:{streaming}:"
            f"{runtime_base_url}:{api_key_signature}"
        )
        if cache_key in self._models_cache:
            return self._models_cache[cache_key]

        if provider == LLMProvider.OPENAI or provider == LLMProvider.LOCAL:
            resolved_base_url = runtime_base_url or (
                settings.LM_STUDIO_BASE_URL if provider == LLMProvider.LOCAL else settings.OPENAI_API_BASE
            )
            resolved_api_key = runtime_api_key or settings.OPENAI_API_KEY
            if not resolved_api_key and not resolved_base_url:
                raise ValueError("OPENAI_API_KEY is not configured")
            # Local OpenAI-compatible providers (LM Studio) do not require a real API key,
            # but the OpenAI client expects a non-empty value.
            if not resolved_api_key:
                resolved_api_key = "local-api-key"

            kwargs = dict(
                model=model_name,
                temperature=temperature,
                max_tokens=max_tokens,
                streaming=streaming,
                api_key=resolved_api_key,
                request_timeout=2.0 if provider == LLMProvider.LOCAL else None
            )
            if resolved_base_url:
                kwargs["base_url"] = resolved_base_url
            model = ChatOpenAI(**kwargs)
        elif provider == LLMProvider.ANTHROPIC:
            resolved_api_key = runtime_api_key or settings.ANTHROPIC_API_KEY
            if not resolved_api_key:
                raise ValueError("ANTHROPIC_API_KEY is not configured")
            model = ChatAnthropic(
                model=model_name,
                temperature=temperature,
                max_tokens=max_tokens,
                streaming=streaming,
                api_key=resolved_api_key,
            )
        elif provider == LLMProvider.GOOGLE:
            resolved_api_key = runtime_api_key or settings.GEMINI_API_KEY or settings.GOOGLE_API_KEY
            if not resolved_api_key:
                raise ValueError("GEMINI_API_KEY/GOOGLE_API_KEY is not configured")
            model = ChatGoogleGenerativeAI(
                model=model_name,
                temperature=temperature,
                max_output_tokens=max_tokens,
                google_api_key=resolved_api_key,
            )
        elif provider == LLMProvider.OLLAMA:
            resolved_base_url = runtime_base_url or settings.OLLAMA_BASE_URL
            model = ChatOllama(
                model=model_name,
                temperature=temperature,
                base_url=resolved_base_url,
            )
        else:
            raise ValueError(f"Unknown provider: {provider}")

        self._models_cache[cache_key] = model
        return model

    def _get_default_provider(self) -> LLMProvider:
        provider = settings.DEFAULT_LLM_PROVIDER
        if isinstance(provider, LLMProvider):
            return provider
        try:
            return LLMProvider(provider)
        except Exception:
            return LLMProvider.OPENAI

    def _resolve_model_name(
        self,
        provider: LLMProvider,
        task_type: str,
        model_override: Optional[str] = None,
    ) -> str:
        if model_override:
            return model_override

        default_provider = self._get_default_provider()
        if provider == default_provider and settings.DEFAULT_MODEL:
            return settings.DEFAULT_MODEL

        tier = self.TASK_ROUTING.get(task_type, {}).get("tier", "default")
        provider_models = self.PROVIDER_MODELS.get(provider, self.PROVIDER_MODELS[LLMProvider.OPENAI])
        return provider_models.get(tier, provider_models["default"])

    def get_model(
        self,
        task_type: str = "general",
        provider_override: Optional[LLMProvider] = None,
        model_override: Optional[str] = None,
        temperature: Optional[float] = None,
        streaming: bool = False,
        runtime_settings: Optional[Dict[str, Any]] = None,
    ) -> BaseChatModel:
        """Get the best model for a specific task."""

        if self._call_count >= settings.API_CALL_BUDGET:
            raise RuntimeError(
                f"API call budget exceeded: {settings.API_CALL_BUDGET}"
            )

        if provider_override and isinstance(provider_override, str):
            provider_override = self._normalize_provider(provider_override)

        if provider_override:
            provider = provider_override
            model_name = self._resolve_model_name(
                provider=provider,
                task_type=task_type,
                model_override=model_override,
            )
        else:
            default_provider = self._get_default_provider()
            routing = self.TASK_ROUTING.get(
                task_type,
                {"provider": default_provider, "tier": "default"},
            )
            provider = routing["provider"]
            if isinstance(provider, str):
                provider = LLMProvider(provider)
            # Prefer the user's configured default provider when it's available,
            # so chat messages use LM Studio / Ollama even though TASK_ROUTING
            # may hard-code a cloud provider for that task type.
            if (
                default_provider in self._available_providers
                and self._provider_available(default_provider, runtime_settings=runtime_settings)
            ):
                provider = default_provider
            
            # Circuit breaker fast-fail for LOCAL provider
            if provider == LLMProvider.LOCAL and not self._local_health_status:
                logger.warning(f"Circuit breaker triggered for {provider}, selecting fallback: {settings.FALLBACK_LLM_PROVIDER.value}")
                provider = settings.FALLBACK_LLM_PROVIDER
                model_override = settings.FALLBACK_MODEL
                
            # Fallback if resolved provider still not available
            if not self._provider_available(provider, runtime_settings=runtime_settings):
                fallback_provider = next(
                    (
                        p
                        for p in self._available_providers
                        if self._provider_available(p, runtime_settings=runtime_settings)
                    ),
                    LLMProvider.OLLAMA,
                )
                provider = fallback_provider
            model_name = self._resolve_model_name(
                provider=provider,
                task_type=task_type,
                model_override=model_override,
            )

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
            runtime_settings=runtime_settings,
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

    async def get_local_models(self, source: LocalModelsSource = LocalModelsSource.LM_STUDIO) -> List[str]:
        """Fetch models from local provider (LM Studio or Ollama)."""
        val = source.value if hasattr(source, "value") else str(source)
        url = settings.LM_STUDIO_BASE_URL if val == "local" else settings.OLLAMA_BASE_URL
        if val == "ollama":
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    resp = await client.get(f"{url.rstrip('/')}/api/tags")
                    if resp.status_code == 200:
                        data = resp.json()
                        return [m["name"] for m in data.get("models", [])]
            except Exception:
                return []
        else:
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    resp = await client.get(f"{url.rstrip('/')}/models")
                    if resp.status_code == 200:
                        data = resp.json()
                        return [m["id"] for m in data.get("data", [])]
            except Exception:
                return []
        return []


# Singleton
llm_router = LLMRouter()


def _sync_persisted_settings_on_startup():
    """Load settings.json at import time and push values into the config singleton.

    This ensures that the last saved provider/model/base_url are used even before
    the first PUT /api/settings call.
    """
    try:
        from app.infrastructure.settings_manager import SettingsManager

        saved = SettingsManager().load()
        _provider_map = {p.value: p for p in LLMProvider}

        persisted_provider = saved.get("llm_provider", "")
        if persisted_provider in _provider_map:
            settings.DEFAULT_LLM_PROVIDER = _provider_map[persisted_provider]
        if saved.get("model_name"):
            settings.DEFAULT_MODEL = saved["model_name"]
        if saved.get("temperature") is not None:
            settings.DEFAULT_TEMPERATURE = float(saved["temperature"])
        if saved.get("max_tokens") is not None:
            settings.DEFAULT_MAX_TOKENS = int(saved["max_tokens"])
        if saved.get("openai_api_key"):
            settings.OPENAI_API_KEY = saved["openai_api_key"]
        if saved.get("openai_api_base") is not None:
            settings.OPENAI_API_BASE = saved["openai_api_base"] or None
        # Propagate LM Studio URL so llm_router resolves it correctly at startup
        if saved.get("llm_provider") == "local" and saved.get("openai_api_base"):
            settings.LM_STUDIO_BASE_URL = saved["openai_api_base"]
        if saved.get("anthropic_api_key"):
            settings.ANTHROPIC_API_KEY = saved["anthropic_api_key"]
        if saved.get("google_api_key"):
            settings.GOOGLE_API_KEY = saved["google_api_key"]
        if saved.get("gemini_api_key"):
            settings.GEMINI_API_KEY = saved["gemini_api_key"]
        if saved.get("ollama_base_url"):
            settings.OLLAMA_BASE_URL = saved["ollama_base_url"]
        if saved.get("e2b_api_key"):
            settings.E2B_API_KEY = saved["e2b_api_key"]
        
        if saved.get("fallback_llm_provider") in _provider_map:
            settings.FALLBACK_LLM_PROVIDER = _provider_map[saved["fallback_llm_provider"]]
        if saved.get("fallback_model_name"):
            settings.FALLBACK_MODEL = saved["fallback_model_name"]

        # Re-detect with updated values
        llm_router._available_providers = llm_router._detect_available_providers()
        llm_router._models_cache.clear()

        logger.info(
            "[LLMRouter] Loaded persisted settings — provider=%s model=%s base_url=%s",
            settings.DEFAULT_LLM_PROVIDER.value,
            settings.DEFAULT_MODEL,
            settings.OPENAI_API_BASE,
        )
    except Exception:  # noqa: BLE001
        logger.debug("[LLMRouter] No persisted settings to load", exc_info=True)


_sync_persisted_settings_on_startup()
