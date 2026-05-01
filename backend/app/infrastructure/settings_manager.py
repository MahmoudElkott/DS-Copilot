"""Settings manager for JSON persistence."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

from app.config import LLMProvider, ExecutionEnv


class SettingsManager:
    """Manages loading and saving user settings to a JSON file."""

    DEFAULT_SETTINGS = {
        "llm_provider": "openai",
        "model_name": "gpt-4o",
        "execution_env": "local",
        "python_interpreter": None,
        "temperature": 0.1,
        "max_tokens": 4096,
        "openai_api_key": None,
        "openai_api_base": None,
        "anthropic_api_key": None,
        "google_api_key": None,
        "gemini_api_key": None,
        "ollama_base_url": "http://localhost:11434",
        "e2b_api_key": None,
        "fallback_llm_provider": "openai",
        "fallback_model_name": "gpt-4o",
    }

    def __init__(self, settings_dir: Optional[str] = None):
        """Initialize the settings manager.

        Args:
            settings_dir: Directory to store settings.json. Defaults to backend root.
        """
        if settings_dir is None:
            settings_dir = Path(__file__).parent.parent.parent
        self.settings_dir = Path(settings_dir)
        self.settings_file = self.settings_dir / "settings.json"

    def load(self) -> Dict[str, Any]:
        """Load settings from settings.json file.

        Returns:
            Dictionary of settings. Returns defaults if file doesn't exist.
        """
        if not self.settings_file.exists():
            return self.DEFAULT_SETTINGS.copy()

        try:
            with open(self.settings_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            return {**self.DEFAULT_SETTINGS, **data}
        except (json.JSONDecodeError, IOError):
            return self.DEFAULT_SETTINGS.copy()

    def save(self, settings: Dict[str, Any]) -> None:
        """Save settings to settings.json file.

        Args:
            settings: Dictionary of settings to save.
        """
        filtered = {
            k: v for k, v in settings.items()
            if k in self.DEFAULT_SETTINGS and v is not None
        }

        self.settings_dir.mkdir(parents=True, exist_ok=True)

        with open(self.settings_file, "w", encoding="utf-8") as f:
            json.dump(filtered, f, indent=2)

    def update(self, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update settings and persist to file.

        Args:
            updates: Dictionary of settings to update.

        Returns:
            Updated settings dictionary.
        """
        current = self.load()
        current.update(updates)
        self.save(current)
        return current
