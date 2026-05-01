# backend/app/api/routers/pipeline.py
import logging
import uuid
import asyncio
from typing import Any, Dict
from fastapi import APIRouter, BackgroundTasks, HTTPException

from app.agent.core.orchestrator import DSOrchestrator, create_initial_state
from app.api.state import active_pipelines, session_metadata
from app.api.websocket import manager as ws_manager
from app.infrastructure.executor import register_execution_log_sink, unregister_execution_log_sink
from app.infrastructure.executor import create_executor
from app.models.schemas import (
    PipelineConfig,
    PipelineStatus,
    PipelineStepInfo,
    PipelineStepStatus,
    SessionCreate,
    SessionInfo,
    NotebookRunRequest,
    NotebookRunResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/pipeline", tags=["pipeline"])

@router.post("/start", response_model=SessionInfo)
async def start_pipeline(config: PipelineConfig, background_tasks: BackgroundTasks):
    """Initialize and start a new pipeline session."""
    session_id = config.session_id or str(uuid.uuid4())
    logger.info(f"🚀 Starting pipeline for session {session_id}")

    # Create initial state
    state = create_initial_state(
        session_id=session_id,
        dataset_path=config.dataset_path,
        project_name=config.project_name,
        user_settings=config.user_settings,
    )

    # Initialize entry in active_pipelines
    active_pipelines[session_id] = {
        "status": "running",
        "state": state,
        "config": config,
    }

    # Define background task to run the pipeline
    async def run_pipeline_task():
        try:
            orchestrator = DSOrchestrator()
            final_state = await orchestrator.run(state)
            
            active_pipelines[session_id]["status"] = "completed"
            active_pipelines[session_id]["final_state"] = final_state
            
            await ws_manager.broadcast({
                "type": "result",
                "agent": "orchestrator",
                "content": "Pipeline completed successfully.",
                "metadata": {
                    "status": "pipeline_complete",
                    "steps_completed": final_state.get("steps_completed", []),
                }
            })
        except Exception as e:
            logger.error(f"❌ Pipeline failed for {session_id}: {e}", exc_info=True)
            active_pipelines[session_id]["status"] = "failed"
            await ws_manager.broadcast({
                "type": "error",
                "agent": "orchestrator",
                "content": f"Pipeline failed: {str(e)}",
            })

    background_tasks.add_task(run_pipeline_task)

    return SessionInfo(
        session_id=session_id,
        status="running",
        project_name=config.project_name
    )

@router.get("/status/{session_id}", response_model=PipelineStatus)
async def get_pipeline_status(session_id: str):
    """Get pipeline status."""
    pipeline_data = active_pipelines.get(session_id)
    if not pipeline_data:
        raise HTTPException(status_code=404, detail="Pipeline not found")

    state = pipeline_data.get("final_state") or pipeline_data.get("state", {})
    steps_completed = state.get("steps_completed", [])
    errors = state.get("errors", [])
    error_map = {
        err.get("step"): err.get("error")
        for err in errors
        if isinstance(err, dict) and err.get("step")
    }

    step_names = [
        ("data_ingest", "Data Ingestion", "DataIngestAgent"),
        ("data_cleaning", "Data Cleaning", "DataCleaningAgent"),
        ("eda", "EDA", "EDAAgent"),
        ("model_selection", "Model Selection", "ModelSelectionAgent"),
        ("code_writing", "Code Writing", "CodeWriterAgent"),
        ("execute_code", "Code Execution", "ExecutionEngine"),
        ("testing", "Testing", "TestingAgent"),
        ("optimization", "Optimization", "OptimizationAgent"),
        ("documentation", "Documentation", "DocumentationAgent"),
    ]

    steps = []
    current_step = state.get("current_step", "unknown")
    for key, name, agent in step_names:
        if key in steps_completed:
            status = PipelineStepStatus.COMPLETED
        elif key in error_map:
            status = PipelineStepStatus.FAILED
        elif key in current_step:
            status = PipelineStepStatus.RUNNING
        else:
            status = PipelineStepStatus.PENDING

        steps.append(
            PipelineStepInfo(
                key=key,
                name=name,
                status=status,
                agent=agent,
                error=error_map.get(key),
                retries=state.get("retry_count", 0) if key == "execute_code" else 0,
            )
        )

    progress = len([step for step in steps if step.status == PipelineStepStatus.COMPLETED])
    progress_percent = (progress / len(step_names)) * 100

    status_value = pipeline_data.get("status", "running")
    if status_value not in {"running", "completed", "failed"}:
        status_value = "running"

    return PipelineStatus(
        session_id=session_id,
        status=status_value,
        current_step=current_step,
        steps=steps,
        progress_percent=round(progress_percent, 1),
    )

@router.post("/rehydrate")
async def rehydrate_pipeline(request: Dict[str, str]):
    """Rehydrate a pipeline session (usually after refresh)."""
    session_id = request.get("session_id")
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id required")
    
    pipeline_data = active_pipelines.get(session_id)
    if not pipeline_data:
        # Check if we can restore from memory/db? For now just return empty if not found
        return {"status": "not_found"}
        
    return {
        "status": pipeline_data.get("status"),
        "state": pipeline_data.get("state"),
        "final_state": pipeline_data.get("final_state")
    }

@router.post("/run-notebook", response_model=NotebookRunResponse)
async def run_notebook_step(request: NotebookRunRequest):
    """Manually run a single notebook cell/step."""
    session_id = request.session_id
    step_key = request.step_key
    
    pipeline_entry = active_pipelines.get(session_id)
    if not pipeline_entry:
        raise HTTPException(status_code=404, detail="Session not found")
        
    state = pipeline_entry.get("state", {})
    code = (state.get("generated_code", {})).get(step_key, "")
    if not code:
         raise HTTPException(status_code=400, detail=f"No code found for step {step_key}")

    executor = create_executor(
        state.get("user_settings", {}).get("execution_env", "local"),
        session_id=session_id,
        python_interpreter=state.get("user_settings", {}).get("python_interpreter")
    )
    
    async def _terminal_sink(data):
        await ws_manager.send_to_session(session_id, {
            "type": "terminal",
            "agent": "notebook",
            "content": data["content"],
            "metadata": {"stream": data["stream"], "step": step_key}
        })

    result = await executor.execute(code, timeout=120, stream_handler=_terminal_sink)
    
    return NotebookRunResponse(
        session_id=session_id,
        step_key=step_key,
        success=result.success,
        exit_code=result.exit_code,
        stdout=result.stdout,
        stderr=result.stderr,
        execution_time=result.execution_time,
        files_created=result.files_created
    )

@router.post("/resume", response_model=SessionInfo)
async def resume_pipeline(config: PipelineConfig, background_tasks: BackgroundTasks):
    """Resume a failed or paused pipeline session."""
    session_id = config.session_id
    if not session_id or session_id not in active_pipelines:
        raise HTTPException(status_code=404, detail="Session not found")
        
    logger.info(f"⏯ Resuming pipeline for session {session_id}")
    
    # Update status to running
    active_pipelines[session_id]["status"] = "running"
    state = active_pipelines[session_id]["state"]
    
    # Clear errors to allow retry
    state["errors"] = []
    
    # Define background task
    async def run_pipeline_task():
        try:
            orchestrator = DSOrchestrator()
            # The orchestrator should handle resuming based on state["steps_completed"].
            final_state = await orchestrator.run(state)
            
            active_pipelines[session_id]["status"] = "completed"
            active_pipelines[session_id]["final_state"] = final_state
            
            await ws_manager.send_to_session(session_id, {
                "type": "result",
                "agent": "orchestrator",
                "content": "Pipeline resumed and completed successfully.",
                "metadata": {
                    "status": "pipeline_complete",
                    "steps_completed": final_state.get("steps_completed", []),
                }
            })
        except Exception as e:
            logger.error(f"❌ Pipeline resume failed for {session_id}: {e}", exc_info=True)
            active_pipelines[session_id]["status"] = "failed"
            await ws_manager.send_to_session(session_id, {
                "type": "error",
                "agent": "orchestrator",
                "content": f"Pipeline resume failed: {str(e)}",
            })

    background_tasks.add_task(run_pipeline_task)
    
    return SessionInfo(
        session_id=session_id,
        status="running",
        project_name=state.get("project_name", "unknown")
    )
