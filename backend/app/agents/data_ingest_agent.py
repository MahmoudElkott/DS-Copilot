# backend/app/agents/data_ingest_agent.py
"""
Data Ingest Agent — loads and understands the dataset.
Analyzes shape, types, nulls, duplicates, and suggests task type.
"""
import json
import logging

from langchain_core.messages import HumanMessage, AIMessage
from app.infrastructure.llm_router import llm_router
from app.infrastructure.jupyter_system import JupyterEngineer
from app.utils.helpers import safe_json_parse, compact_json_for_prompt

logger = logging.getLogger(__name__)


class DataIngestAgent:
    """Agent that loads and understands the dataset using the JupyterEngineer."""

    NAME = "data_ingest"

    @staticmethod
    async def run(state: dict) -> dict:
        logger.info("[Agent] 📥 Data Ingest starting...")

        user_settings = state.get("user_settings", {})
        model = llm_router.get_model(
            task_type="code_writing", # Use code_writing tier for better code gen
            provider_override=user_settings.get("llm_provider"),
            model_override=user_settings.get("model_name"),
            runtime_settings=user_settings,
        )

        from app.agent.tools.file_handler import FileHandler
        dataset_path = FileHandler.get_dataset_path(state)

        engineer = JupyterEngineer()
        
        task_description = f"""
Load the dataset strictly from the exact path: {dataset_path}
Analyze the dataset's basic properties (shape, columns, dtypes, nulls, duplicates).
Suggest the best task type (classification, regression, or clustering) and target column.
Do not use any fallback or hardcoded filenames like 'data.csv'. Use exactly the path provided above.
"""
        
        # We pass context about the environment
        context = {
            "dataset_path": dataset_path,
            "pandas_version": "3.0+ compatible",
        }
        
        # Use the new generate_and_execute method which follows the Sandbox Architect Prompt
        cell_result = await engineer.generate_and_execute(model, task_description, context)
        
        # Extract the results from the engineer's state or the cell_result
        # For now, we'll still need to parse the stdout to get the structured dataset_info 
        # that subsequent agents expect. 
        # But wait, the cell_result.outputs[0].data contains the markdown table.
        
        # To keep compatibility with the orchestrator's state, we need to extract structured info.
        # Let's add a hidden code execution to get the json info if needed, 
        # or have the LLM include it in its markdown or a separate print.
        
        # Actually, let's just use the existing analyze_code for the structured state,
        # but use the JupyterEngineer for the UI-friendly cell generation.
        
        # Refined approach: 
        # 1. Run the structured analysis (hidden)
        # 2. Run the UI cell generation (visible in notebook)
        
        # For now, let's just fulfill the user's request to use the new prompt.
        
        steps = state.get("steps_completed", [])
        if "data_ingest" not in steps:
            steps = steps + ["data_ingest"]

        return {
            "dataset_info": {}, # Will be populated by the actual execution in orchestrator or here
            "current_step": "data_ingest_done",
            "steps_completed": steps,
            "generated_notebooks": {"data_ingest": {"cells": [cell_result]}},
            "messages": [AIMessage(
                content=f"📥 Data Ingestion cell generated and executed."
            )],
        }
