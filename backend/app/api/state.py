# backend/app/api/state.py
from typing import Any, Dict
from app.infrastructure.settings_manager import SettingsManager

# In-memory state for active pipelines
# Maps session_id -> { "status": str, "state": dict, "final_state": dict, "task": Task }
active_pipelines: Dict[str, Dict[str, Any]] = {}

# Session metadata (e.g. connected users, timestamps)
session_metadata: Dict[str, Dict[str, Any]] = {}

# Settings manager for JSON persistence
settings_manager = SettingsManager()

# WebSocket connection manager
from app.api.websocket import manager as ws_manager
