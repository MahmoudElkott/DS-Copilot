# backend/app/agents/data_cleaning_agent.py
"""
Data Cleaning Agent — cleans and preprocesses data.
Handles missing values, duplicates, outliers, type fixes, encoding.
"""
import json
import logging

from langchain_core.messages import HumanMessage, AIMessage
from app.infrastructure.llm_router import llm_router
from app.infrastructure.jupyter_system import JupyterEngineer
from app.utils.helpers import extract_code, safe_json_parse, compact_json_for_prompt

logger = logging.getLogger(__name__)


class DataCleaningAgent:
    """Agent that cleans and preprocesses data using JupyterEngineer."""

    NAME = "data_cleaning"

    @staticmethod
    async def run(state: dict) -> dict:
        logger.info("[Agent] 🧹 Data Cleaning starting...")

        user_settings = state.get("user_settings", {})
        model = llm_router.get_model(
            task_type="code_writing",
            provider_override=user_settings.get("llm_provider"),
            model_override=user_settings.get("model_name"),
            runtime_settings=user_settings,
        )
        dataset_info = state.get("dataset_info", {})
        
        from app.agent.tools.file_handler import FileHandler
        dataset_path = FileHandler.get_dataset_path(state)
        output_path = FileHandler.get_output_path("processed", "cleaned_data.csv")
        
        engineer = JupyterEngineer()
        
        task_description = f"""
Clean and preprocess the dataset.
1. Load from {dataset_path}
2. Handle missing values, duplicates, and fix types.
3. Handle outliers using IQR.
4. Encode categorical variables.
5. Save cleaned data to {output_path}
"""
        
        context = {
            "dataset_info": dataset_info,
            "dataset_path": dataset_path,
            "output_path": output_path
        }
        
        cell_result = await engineer.generate_and_execute(model, task_description, context)

        return {
            "cleaning_result": {"file_path": output_path},
            "current_step": "cleaning_done",
            "steps_completed": state.get("steps_completed", []) + ["data_cleaning"],
            "generated_notebooks": {
                **state.get("generated_notebooks", {}),
                "data_cleaning": {"cells": [cell_result]}
            },
            "messages": [AIMessage(content="🧹 Data cleaning cell generated and executed.")],
        }
