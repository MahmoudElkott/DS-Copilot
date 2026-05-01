# backend/app/api/routers/settings.py
import logging
from typing import Any, Dict, List
from fastapi import APIRouter, HTTPException

from app.api.state import active_pipelines, settings_manager
from app.config import LLMProvider, ExecutionEnv, settings
from app.infrastructure.llm_router import llm_router
from app.models.schemas import (
    SettingsResponse, SettingsUpdate, StatsResponse,
    PythonInterpretersResponse, LocalModelsResponse, LocalModelsSource, LocalModelsSourceInfo
)
from app.utils.system import discover_python_interpreters

logger = logging.getLogger(__name__)

router = APIRouter(tags=["settings"])

@router.get("/settings", response_model=SettingsResponse)
async def get_settings():
    """Get current settings."""
    saved = settings_manager.load()
    return SettingsResponse(
        llm_provider=saved.get("llm_provider", settings.DEFAULT_LLM_PROVIDER.value),
        model_name=saved.get("model_name", settings.DEFAULT_MODEL),
        execution_env=saved.get("execution_env", settings.DEFAULT_EXECUTION_ENV.value),
        python_interpreter=saved.get("python_interpreter", settings.DEFAULT_PYTHON_INTERPRETER),
        temperature=saved.get("temperature", settings.DEFAULT_TEMPERATURE),
        max_tokens=saved.get("max_tokens", settings.DEFAULT_MAX_TOKENS),
        available_providers=[p.value for p in llm_router._available_providers],
        openai_api_base=saved.get("openai_api_base", settings.OPENAI_API_BASE),
        ollama_base_url=saved.get("ollama_base_url", settings.OLLAMA_BASE_URL),
        openai_api_key_loaded=bool(saved.get("openai_api_key") or settings.OPENAI_API_KEY),
        anthropic_api_key_loaded=bool(saved.get("anthropic_api_key") or settings.ANTHROPIC_API_KEY),
        gemini_api_key_loaded=bool(saved.get("gemini_api_key") or saved.get("google_api_key") or settings.GEMINI_API_KEY or settings.GOOGLE_API_KEY),
        e2b_api_key_loaded=bool(saved.get("e2b_api_key") or settings.E2B_API_KEY),
    )

@router.put("/settings", response_model=SettingsResponse)
async def update_settings(update: SettingsUpdate):
    """Update settings."""
    updates = {}
    if update.llm_provider:
        try:
            updates["llm_provider"] = LLMProvider(update.llm_provider).value
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid provider: {update.llm_provider}")
            
    if update.model_name: updates["model_name"] = update.model_name
    if update.execution_env:
        try:
            updates["execution_env"] = ExecutionEnv(update.execution_env).value
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid env: {update.execution_env}")
            
    if update.python_interpreter is not None: updates["python_interpreter"] = update.python_interpreter.strip() or None
    if update.temperature is not None: updates["temperature"] = update.temperature
    if update.max_tokens is not None: updates["max_tokens"] = update.max_tokens
    if update.openai_api_key is not None: updates["openai_api_key"] = update.openai_api_key.strip() or None
    if update.openai_api_base is not None: updates["openai_api_base"] = update.openai_api_base.strip() or None
    if update.anthropic_api_key is not None: updates["anthropic_api_key"] = update.anthropic_api_key.strip() or None
    if update.google_api_key is not None: updates["google_api_key"] = update.google_api_key.strip() or None
    if update.gemini_api_key is not None: updates["gemini_api_key"] = update.gemini_api_key.strip() or None
    if update.ollama_base_url is not None: updates["ollama_base_url"] = update.ollama_base_url.strip() or "http://localhost:11434"
    if update.e2b_api_key is not None: updates["e2b_api_key"] = update.e2b_api_key.strip() or None

    saved = settings_manager.update(updates)

    # Sync to runtime config
    if "llm_provider" in updates: settings.DEFAULT_LLM_PROVIDER = LLMProvider(updates["llm_provider"])
    if "model_name" in updates: settings.DEFAULT_MODEL = updates["model_name"]
    if "temperature" in updates: settings.DEFAULT_TEMPERATURE = float(updates["temperature"])
    if "max_tokens" in updates: settings.DEFAULT_MAX_TOKENS = int(updates["max_tokens"])
    if "openai_api_key" in updates: settings.OPENAI_API_KEY = updates["openai_api_key"]
    if "openai_api_base" in updates: settings.OPENAI_API_BASE = updates["openai_api_base"]
    if updates.get("llm_provider") == "local" and updates.get("openai_api_base"):
        settings.LM_STUDIO_BASE_URL = updates["openai_api_base"]
    
    # Flush cache
    llm_router._available_providers = llm_router._detect_available_providers()
    llm_router._models_cache.clear()
    
    return await get_settings()

@router.get("/system/python-interpreters", response_model=PythonInterpretersResponse)
async def list_python_interpreters():
    """List Python interpreters."""
    return PythonInterpretersResponse(interpreters=discover_python_interpreters())

@router.get("/stats", response_model=StatsResponse)
async def get_stats():
    """Get usage stats."""
    stats = llm_router.get_stats()
    return StatsResponse(
        total_calls=stats["total_calls"],
        budget_remaining=stats["budget_remaining"],
        available_providers=stats["available_providers"],
        active_sessions=len(active_pipelines),
    )

@router.get("/llm/local-models", response_model=LocalModelsResponse)
async def get_local_models(source: LocalModelsSource = LocalModelsSource.LM_STUDIO):
    """List models from a local provider."""
    models = await llm_router.get_local_models(source)
    return LocalModelsResponse(
        models=models, 
        sources=[LocalModelsSourceInfo(
            provider=source.value,
            base_url=settings.LM_STUDIO_BASE_URL if source == LocalModelsSource.LM_STUDIO else settings.OLLAMA_BASE_URL,
            success=True,
            model_count=len(models)
        )]
    )
