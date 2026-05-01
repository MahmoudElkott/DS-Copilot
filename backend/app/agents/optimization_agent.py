# backend/app/agents/optimization_agent.py
"""
Optimization Agent — performs hyperparameter tuning and model optimization.
Uses GridSearchCV/RandomizedSearchCV, cross-validation, and feature importance.
"""
import json
import logging

from langchain_core.messages import HumanMessage, AIMessage
from app.infrastructure.llm_router import llm_router
from app.infrastructure.jupyter_system import JupyterEngineer
from app.utils.helpers import extract_code, safe_json_parse, compact_json_for_prompt

logger = logging.getLogger(__name__)


class OptimizationAgent:
    """Agent that optimizes model hyperparameters using JupyterEngineer."""

    NAME = "optimization"

    @staticmethod
    async def run(state: dict) -> dict:
        logger.info("[Agent] ⚡ Optimization starting...")

        user_settings = state.get("user_settings", {})
        model = llm_router.get_model(
            task_type="code_writing",
            provider_override=user_settings.get("llm_provider"),
            model_override=user_settings.get("model_name"),
            runtime_settings=user_settings,
        )
        
        engineer = JupyterEngineer()
        
        dataset_info = state.get("dataset_info", {})
        model_selection = state.get("model_selection_result", {})
        training_result = state.get("training_result", {})

        task_description = f"""
Optimize the best performing model.
1. Load cleaned data from data/processed/cleaned_data.csv.
2. Load best model from output/models/best_model.pkl.
3. Perform hyperparameter tuning (RandomizedSearchCV).
4. Analyze feature importance and save plot to output/figures/feature_importance.png.
5. Save optimized model to output/models/optimized_model.pkl.
"""
        
        context = {
            "dataset_info": dataset_info,
            "model_selection": model_selection,
            "training_result": training_result,
            "paths": {
                "input": "data/processed/cleaned_data.csv",
                "best_model": "output/models/best_model.pkl",
                "optimized_model": "output/models/optimized_model.pkl",
                "importance_plot": "output/figures/feature_importance.png"
            }
        }
        
        cell_result = await engineer.generate_and_execute(model, task_description, context)

        return {
            "optimization_result": {},
            "current_step": "optimization_done",
            "steps_completed": state.get("steps_completed", []) + ["optimization"],
            "generated_notebooks": {
                **state.get("generated_notebooks", {}),
                "optimization": {"cells": [cell_result]}
            },
            "messages": [AIMessage(content="⚡ Optimization cell generated and executed.")],
        }
