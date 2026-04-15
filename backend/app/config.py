# backend/app/config.py
from pydantic_settings import BaseSettings
from typing import Optional
from enum import Enum


class LLMProvider(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    OLLAMA = "ollama"


class ExecutionEnv(str, Enum):
    LOCAL = "local"
    E2B = "e2b"


class Settings(BaseSettings):
    # === App ===
    APP_NAME: str = "DS-Copilot"
    DEBUG: bool = True
    SECRET_KEY: str = "change-me-in-production"

    # === LLM Providers ===
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_API_BASE: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    GOOGLE_API_KEY: Optional[str] = None
    OLLAMA_BASE_URL: str = "http://localhost:11434"

    # === Default LLM ===
    DEFAULT_LLM_PROVIDER: LLMProvider = LLMProvider.OPENAI
    DEFAULT_MODEL: str = "gpt-4o"
    DEFAULT_TEMPERATURE: float = 0.1
    DEFAULT_MAX_TOKENS: int = 4096

    # === Execution ===
    DEFAULT_EXECUTION_ENV: ExecutionEnv = ExecutionEnv.LOCAL
    E2B_API_KEY: Optional[str] = None
    LOCAL_SANDBOX_DIR: str = "./sandbox"

    # === Database ===
    DATABASE_URL: str = "sqlite:///./ds_copilot.db"
    REDIS_URL: str = "redis://localhost:6379"

    # === Git ===
    ENABLE_GIT: bool = True
    GIT_AUTO_COMMIT: bool = True

    # === Output ===
    OUTPUT_DIR: str = "./output"
    MAX_RETRIES: int = 3
    API_CALL_BUDGET: int = 100

    class Config:
        env_file = ".env"


settings = Settings()
