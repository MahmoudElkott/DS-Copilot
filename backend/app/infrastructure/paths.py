import os
from pathlib import Path
from typing import Dict

class GlobalPathManager:
    @staticmethod
    def get_context_config(sandbox_dir: str, dataset_path: str) -> Dict[str, str]:
        # Resolve to absolute paths to prevent agent guessing
        base_dir = Path(__file__).parent.parent.parent.resolve() # /backend
        
        # If dataset_path is already absolute, use it, else resolve relative to base
        data_path = Path(dataset_path)
        if not data_path.is_absolute():
            data_path = base_dir / dataset_path

        workspace_root = base_dir.parent.resolve() # /DS-Copilot
        output_path = workspace_root / "storage"
        
        return {
            "DATA_PATH": str(data_path.resolve()),
            "OUTPUT_PATH": str(output_path.resolve()),
            "WORKSPACE_ROOT": str(workspace_root.resolve()),
            "SANDBOX_DIR": str(Path(sandbox_dir).resolve())
        }
