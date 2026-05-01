# backend/app/api/routers/files.py
import logging
import os
import shutil
import uuid
from typing import Any, Dict
from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.api.state import active_pipelines
from app.config import settings
from app.infrastructure.file_manager import FileManager
from app.models.schemas import FileTreeResponse, FileUploadResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/files", tags=["files"])

def _build_sandbox_tree() -> dict:
    """Build a lightweight tree for user-visible sandbox artifacts."""
    sandbox_dir = os.path.abspath(settings.LOCAL_SANDBOX_DIR)
    if not os.path.exists(sandbox_dir):
        return {}

    include_dirs = {"data", "output"}
    include_exts = {
        ".csv", ".xlsx", ".xls", ".json", ".txt", ".md", ".py", ".pkl",
        ".png", ".jpg", ".jpeg",
    }

    file_manager = FileManager()
    full_tree = file_manager.get_file_tree(sandbox_dir)
    sandbox_tree = {}

    for name, value in full_tree.items():
        if name in include_dirs and isinstance(value, dict):
            sandbox_tree[name] = value
            continue
        
        # Keep only allowed extensions at root if any
        if value is None: # File
            _, ext = os.path.splitext(name)
            if ext.lower() in include_exts:
                sandbox_tree[name] = value

    return sandbox_tree

@router.post("/upload", response_model=FileUploadResponse)
async def upload_file(file: UploadFile = File(...)):
    """Upload a dataset to the local sandbox."""
    sandbox_dir = os.path.abspath(settings.LOCAL_SANDBOX_DIR)
    data_dir = os.path.join(sandbox_dir, "data")
    os.makedirs(data_dir, exist_ok=True)

    file_path = os.path.join(data_dir, file.filename)
    
    # Save file
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    logger.info(f"📁 File uploaded: {file.filename} -> {file_path}")

    return FileUploadResponse(
        filename=file.filename,
        path=file_path,
        size=os.path.getsize(file_path),
        timestamp=os.path.getmtime(file_path)
    )

@router.get("/{session_id}", response_model=FileTreeResponse)
async def get_file_tree(session_id: str):
    """Get the project file tree."""
    pipeline_data = active_pipelines.get(session_id, {})
    state = pipeline_data.get("final_state") or pipeline_data.get("state", {})
    project_dir = state.get("project_dir", "")

    tree = {}

    if project_dir and os.path.exists(project_dir):
        file_manager = FileManager()
        tree["project"] = file_manager.get_file_tree(project_dir)

    sandbox_tree = _build_sandbox_tree()
    if sandbox_tree:
        tree["sandbox"] = sandbox_tree

    return FileTreeResponse(
        project_name=state.get("project_name", "unknown"),
        tree=tree,
    )

@router.get("/{session_id}/download/{filepath:path}")
async def download_file(session_id: str, filepath: str):
    """Download a file from the project."""
    pipeline_data = active_pipelines.get(session_id, {})
    state = pipeline_data.get("final_state") or pipeline_data.get("state", {})
    project_dir = state.get("project_dir", "")

    sandbox_dir = os.path.abspath(settings.LOCAL_SANDBOX_DIR)
    rel_path = filepath.replace("\\", "/")

    if rel_path.startswith("project/"):
        rel_path = rel_path[len("project/"):]
        base_dir = project_dir
    elif rel_path.startswith("sandbox/"):
        rel_path = rel_path[len("sandbox/"):]
        base_dir = sandbox_dir
    else:
        base_dir = project_dir

    full_path = os.path.join(base_dir, rel_path)
    if not os.path.exists(full_path):
        raise HTTPException(status_code=404, detail="File not found")

    if not os.path.abspath(full_path).startswith(os.path.abspath(base_dir)):
        raise HTTPException(status_code=403, detail="Access denied")

    return FileResponse(full_path)

@router.get("/{session_id}/artifact/{filename:path}")
async def get_artifact(session_id: str, filename: str):
    """Fetch an artifact (image/json) by filename for lazy loading."""
    pipeline_data = active_pipelines.get(session_id, {})
    state = pipeline_data.get("final_state") or pipeline_data.get("state", {})
    project_dir = state.get("project_dir", "")
    
    # Resolve correct project path if possible
    if not project_dir:
        project_dir = os.path.abspath(settings.OUTPUT_DIR)

    full_path = os.path.join(project_dir, filename)
    if not os.path.exists(full_path):
        # Check subdirectories like 'plots'
        alt_path = os.path.join(project_dir, "plots", filename)
        if os.path.exists(alt_path):
            full_path = alt_path
        else:
            raise HTTPException(status_code=404, detail=f"Artifact {filename} not found in {project_dir}")

    output_root = os.path.abspath(settings.OUTPUT_DIR)
    if not os.path.abspath(full_path).startswith(os.path.abspath(project_dir)) and not os.path.abspath(full_path).startswith(output_root):
        raise HTTPException(status_code=403, detail="Access denied")

    return FileResponse(full_path)
