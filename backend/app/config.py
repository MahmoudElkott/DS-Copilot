import os
from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import ConfigDict, Field
from typing import Optional
from enum import Enum


class LLMProvider(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    OLLAMA = "ollama"
    LOCAL = "local"


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
    GEMINI_API_KEY: Optional[str] = None
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    LM_STUDIO_BASE_URL: str = "http://localhost:1234/v1"

    # === Default LLM ===
    DEFAULT_LLM_PROVIDER: LLMProvider = LLMProvider.OPENAI
    DEFAULT_MODEL: str = "gpt-4o"
    FALLBACK_LLM_PROVIDER: LLMProvider = LLMProvider.GOOGLE
    FALLBACK_MODEL: str = "gemini-1.5-pro"
    DEFAULT_TEMPERATURE: float = 0.1
    DEFAULT_MAX_TOKENS: int = 4096

    # === Execution ===
    DEFAULT_EXECUTION_ENV: ExecutionEnv = ExecutionEnv.LOCAL
    DEFAULT_PYTHON_INTERPRETER: Optional[str] = None
    E2B_API_KEY: Optional[str] = None
    LOCAL_SANDBOX_DIR: str = "./sandbox"

    # === Database ===
    @property
    def DATABASE_PATH(self) -> Path:
        base_dir = Path(__file__).parent.parent
        db_dir = base_dir / "data" / "db"
        db_dir.mkdir(parents=True, exist_ok=True)
        return db_dir / "ds_copilot.db"

    @property
    def DATABASE_URL(self) -> str:
        return f"sqlite:///{self.DATABASE_PATH.absolute()}"

    REDIS_URL: str = "redis://localhost:6379"

    # === Git ===
    ENABLE_GIT: bool = True
    GIT_AUTO_COMMIT: bool = True

    # === Output ===
    OUTPUT_DIR: str = "../storage"
    MAX_RETRIES: int = 3
    API_CALL_BUDGET: int = 100

    model_config = ConfigDict(env_file=".env", extra="ignore")


settings = Settings()
