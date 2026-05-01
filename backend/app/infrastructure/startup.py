# backend/app/core/startup.py
"""
Startup checks and initialization.
Runs on FastAPI app startup to validate configuration
and prepare the runtime environment.
"""
import os
import sys
import logging
from typing import Any, Dict, List

from app.config import settings

logger = logging.getLogger(__name__)


def check_llm_providers() -> Dict[str, bool]:
    """Validate that at least one LLM provider is configured."""
    providers = {
        "openai": bool(settings.OPENAI_API_KEY),
        "anthropic": bool(settings.ANTHROPIC_API_KEY),
        "google": bool(settings.GOOGLE_API_KEY),
        "ollama": True,  # Always potentially available locally
    }

    configured = [name for name, available in providers.items() if available]

    if not configured:
        logger.error(
            "❌ No LLM providers configured! "
            "Set at least one of: OPENAI_API_KEY, ANTHROPIC_API_KEY, GOOGLE_API_KEY"
        )
    else:
        logger.info(f"✅ LLM providers available: {', '.join(configured)}")

    return providers


def check_sandbox_directory() -> bool:
    """Ensure the sandbox directory exists and is writable."""
    sandbox_dir = os.path.abspath(settings.LOCAL_SANDBOX_DIR)
    try:
        os.makedirs(sandbox_dir, exist_ok=True)
        # Test write permission
        test_file = os.path.join(sandbox_dir, ".write_test")
        with open(test_file, "w") as f:
            f.write("test")
        os.remove(test_file)
        logger.info(f"✅ Sandbox directory ready: {sandbox_dir}")
        return True
    except Exception as e:
        logger.error(f"❌ Sandbox directory error ({sandbox_dir}): {e}")
        return False


def check_output_directory() -> bool:
    """Ensure the output directory exists and is writable."""
    output_dir = os.path.abspath(settings.OUTPUT_DIR)
    try:
        os.makedirs(output_dir, exist_ok=True)
        logger.info(f"✅ Output directory ready: {output_dir}")
        return True
    except Exception as e:
        logger.error(f"❌ Output directory error ({output_dir}): {e}")
        return False


def initialize_database() -> bool:
    """Initialize database tables."""
    try:
        from app.infrastructure.memory import memory  # noqa: F401 — triggers table creation
        logger.info("✅ Database initialized")
        return True
    except Exception as e:
        logger.error(f"❌ Database initialization error: {e}")
        return False


def log_system_info():
    """Log system information for debugging."""
    logger.info("=" * 60)
    logger.info(f"🚀 {settings.APP_NAME} Starting Up")
    logger.info("=" * 60)
    logger.info(f"  Python version: {sys.version}")
    logger.info(f"  Debug mode: {settings.DEBUG}")
    logger.info(f"  Database: {settings.DATABASE_URL}")
    logger.info(f"  Sandbox: {os.path.abspath(settings.LOCAL_SANDBOX_DIR)}")
    logger.info(f"  Output: {os.path.abspath(settings.OUTPUT_DIR)}")
    logger.info(f"  Default LLM: {settings.DEFAULT_LLM_PROVIDER}:{settings.DEFAULT_MODEL}")
    logger.info(f"  Execution env: {settings.DEFAULT_EXECUTION_ENV}")
    logger.info(f"  Git enabled: {settings.ENABLE_GIT}")
    logger.info(f"  API call budget: {settings.API_CALL_BUDGET}")
    logger.info("=" * 60)


async def run_startup_checks() -> Dict[str, Any]:
    """Run all startup checks and return results."""

    log_system_info()

    results = {
        "llm_providers": check_llm_providers(),
        "sandbox_ready": check_sandbox_directory(),
        "output_ready": check_output_directory(),
        "database_ready": initialize_database(),
    }

    # Summary
    all_ok = results["sandbox_ready"] and results["output_ready"] and results["database_ready"]

    if all_ok:
        logger.info("✅ All startup checks passed!")
    else:
        failed = [k for k, v in results.items() if v is False]
        logger.warning(f"⚠️ Some startup checks failed: {failed}")

    return results
