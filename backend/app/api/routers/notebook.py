# backend/app/api/routers/notebook.py
import os
import subprocess
import shutil
import logging
from fastapi import APIRouter, HTTPException
from datetime import datetime, timezone

from app.api.state import settings_manager, ws_manager
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/notebook", tags=["notebook"])

def _maybe_emit_viz_payload(output_text: str):
    """Parse output for profiling data and broadcast."""
    import asyncio
    if not output_text.strip(): return

    payload = {}
    lines = output_text.strip().split("\n")
    if len(lines) > 3:
        has_numbers = any(
            any(c.replace(".", "").replace("-", "").replace("e", "").isdigit() for c in line.split())
            for line in lines[1:5]
        )
        if has_numbers:
            payload["profiling_output"] = output_text
            payload["profiling_timestamp"] = datetime.now(timezone.utc).isoformat()

    if payload:
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(ws_manager.broadcast({
                    "type": "result",
                    "agent": "executor",
                    "content": "Profiling data available",
                    "metadata": {
                        "visualization_payload": payload,
                        "status": "profiling_complete",
                    },
                }))
        except Exception: pass

@router.post("/execute")
async def execute_notebook_cell(request: dict):
    """Execute a Python code cell."""
    code = request.get("code", "")
    timeout = request.get("timeout", 30)

    if not code.strip():
        raise HTTPException(status_code=400, detail="No code provided.")

    saved = settings_manager.load()
    python_path = saved.get("python_interpreter") or settings.DEFAULT_PYTHON_INTERPRETER
    if not python_path:
        python_path = shutil.which("python3") or shutil.which("python")
    
    if not python_path:
        raise HTTPException(status_code=500, detail="No Python interpreter configured.")

    sandbox_dir = os.path.abspath(settings.LOCAL_SANDBOX_DIR)
    os.makedirs(sandbox_dir, exist_ok=True)

    try:
        proc = subprocess.run(
            [python_path, "-c", code],
            capture_output=True, text=True, timeout=timeout, cwd=sandbox_dir,
            env={**os.environ, "MPLBACKEND": "Agg"}
        )
        _maybe_emit_viz_payload(proc.stdout or "")
        return {
            "output": proc.stdout or "",
            "error": proc.stderr or "",
            "exit_code": proc.returncode,
        }
    except subprocess.TimeoutExpired:
        return {"output": "", "error": f"Timeout after {timeout}s", "exit_code": -1}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Execution error: {exc}")
