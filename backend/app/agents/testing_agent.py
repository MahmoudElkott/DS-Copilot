# backend/app/agents/testing_agent.py
"""
Testing Agent — generates and runs pytest tests for the ML pipeline.
Uses TDD approach via harness engine.
"""
import json
import logging

from langchain_core.messages import HumanMessage, AIMessage
from app.infrastructure.llm_router import llm_router
from app.infrastructure.jupyter_system import JupyterEngineer
from app.utils.helpers import extract_code, compact_json_for_prompt

logger = logging.getLogger(__name__)


class TestingAgent:
    """Agent that generates and runs tests using JupyterEngineer and standard asserts."""

    NAME = "testing"

    @staticmethod
    async def run(state: dict) -> dict:
        logger.info("[Agent] 🧪 Testing starting...")

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

        task_description = """
Verify the integrity of the ML pipeline using standard Python asserts.
1. Test data loading from data/processed/cleaned_data.csv (existence, shape, nulls).
2. Test model loading from output/models/best_model.pkl and prediction capability.
3. Verify pipeline integrity (performance above baseline).
4. Test edge cases (single row prediction).
Do NOT use pytest. Use standard assert statements.
"""
        
        context = {
            "dataset_info": dataset_info,
            "model_selection": model_selection,
            "training_result": training_result,
            "paths": {
                "data": "data/processed/cleaned_data.csv",
                "model": "output/models/best_model.pkl"
            }
        }
        
        cell_result = await engineer.generate_and_execute(model, task_description, context)

        return {
            "testing_result": {},
            "current_step": "testing_done",
            "steps_completed": state.get("steps_completed", []) + ["testing"],
            "generated_notebooks": {
                **state.get("generated_notebooks", {}),
                "testing": {"cells": [cell_result]}
            },
            "messages": [AIMessage(content="🧪 Pipeline testing cell generated and executed.")],
        }
