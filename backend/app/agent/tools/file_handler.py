from pathlib import Path
import os
from typing import Any, Dict, Optional, Iterable

from app.config import settings

class FileHandler:
    """Handles dynamic pathing and file operations for agents."""
    
    @staticmethod
    def get_dataset_path(state: Dict[str, Any]) -> str:
        """
        Dynamically resolve the dataset path from state.
        """
        cleaning_result = state.get("cleaning_result", {})
        path = cleaning_result.get("file_path") or state.get("dataset_path") or "data/raw/data.csv"
        return str(Path(path).resolve())
    @staticmethod
    def get_directory(category: str) -> str:
        """
        Resolves the absolute path for a specific category directory.
        """
        base_dir = Path(os.getenv("OUTPUT_PATH", settings.OUTPUT_DIR))
        category_map = {
            "raw": base_dir / "raw",
            "processed": base_dir / "processed",
            "models": base_dir / "models",
            "plots": base_dir / "plots",
            "reports": base_dir / "reports"
        }
        target_dir = category_map.get(category, base_dir)
        target_dir.mkdir(parents=True, exist_ok=True)
        return str(target_dir.resolve())

    @staticmethod
    def get_output_path(category: str, filename: str, state: Optional[Dict[str, Any]] = None) -> str:
        """
        Generates a standardized output path based on category.
        """
        dir_path = Path(FileHandler.get_directory(category))
        return str((dir_path / filename).resolve())

    @staticmethod
    def get_allowed_paths(
        state: Optional[Dict[str, Any]] = None,
        context_config: Optional[Dict[str, str]] = None,
        sandbox_dir: Optional[str] = None,
    ) -> tuple[Path, ...]:
        """Collect the filesystem roots generated code is allowed to touch."""
        allowed: list[Path] = []

        def add(value: Any) -> None:
            if not value:
                return
            try:
                resolved = Path(value).expanduser().resolve()
            except Exception:
                return
            if resolved not in allowed:
                allowed.append(resolved)

        add(Path(os.getenv("OUTPUT_PATH", settings.OUTPUT_DIR)))
        if sandbox_dir:
            add(sandbox_dir)

        if context_config:
            for key in ("SANDBOX_DIR", "OUTPUT_PATH", "WORKSPACE_ROOT", "DATA_PATH"):
                add(context_config.get(key))
            data_path = context_config.get("DATA_PATH")
            if data_path:
                add(Path(data_path).parent)

        if state:
            add(state.get("project_dir"))
            add(state.get("dataset_path"))
            cleaning_result = state.get("cleaning_result", {})
            if isinstance(cleaning_result, dict):
                add(cleaning_result.get("file_path"))

        return tuple(sorted(allowed, key=str))

    @staticmethod
    def inject_path_into_prompt(prompt: str, state: Dict[str, Any]) -> str:
        """Injects the dynamic dataset path into a system prompt."""
        path = FileHandler.get_dataset_path(state)
        return prompt.replace("{dataset_path}", path)
