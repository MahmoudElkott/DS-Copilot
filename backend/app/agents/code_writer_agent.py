"""
Code Writer Agent.
Generates a notebook-style training pipeline as interleaved markdown + code cells.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.infrastructure.llm_router import llm_router
from app.infrastructure.utils import CodeSplitter
from app.utils.helpers import safe_json_parse

logger = logging.getLogger(__name__)


class CodeWriterAgent:
    """Agent that generates the training pipeline using the JupyterEngineer."""

    NAME = "code_writer"

    @staticmethod
    async def run(state: dict) -> dict:
        logger.info("[Agent] Code Writer starting notebook generation...")

        user_settings = state.get("user_settings", {})
        model = llm_router.get_model(
            task_type="code_writing",
            provider_override=user_settings.get("llm_provider"),
            model_override=user_settings.get("model_name"),
            runtime_settings=user_settings,
        )

        dataset_info = state.get("dataset_info", {})
        model_selection = state.get("model_selection_result", {})
        task_type = model_selection.get("task_type", "classification")
        target_col = model_selection.get("target_column", None)
        recommended_models = model_selection.get("recommended_models", [])

        from app.agent.tools.file_handler import FileHandler
        # Input is the cleaned data from previous step
        input_path = FileHandler.get_dataset_path(state)
        # Output is the model path
        model_path = FileHandler.get_output_path("models", "best_model.pkl")
        
        system_prompt = """
You are a Lead Data Science Engineer. Your task is to write a COMPLETE training pipeline for the given task.
You must use a "Modular Cell Architecture".
Every logical step (Imports, Loading, Cleaning, EDA, Training) MUST be wrapped in its own cell delimiter using exactly this format:
### CELL: [CELL_NAME]
[PYTHON CODE HERE]

Do not combine EDA visualizations with Model Training in the same block. Write raw python code only. Do not output markdown except for the cell delimiters.
"""
        user_message = f"""
Task Type: {task_type}
Target Column: {target_col}
Models to train: {recommended_models}
Load data from {input_path}.
Train, evaluate, and save the best model to {model_path}.

Context:
{dataset_info}
"""
        messages = [
            SystemMessage(content=system_prompt.strip()),
            HumanMessage(content=user_message.strip()),
        ]

        response = await model.ainvoke(messages)
        raw_code = response.content

        cells = CodeSplitter.parse_cells(raw_code, stage="code_writing")
        
        # We also concatenate the code for the execute_code_node to run
        full_executable_code = "\n\n".join([cell["content"] for cell in cells])

        generated_code = dict(state.get("generated_code", {}))
        generated_code["code_writing"] = full_executable_code

        steps = state.get("steps_completed", [])
        if "code_writing" not in steps:
            steps = steps + ["code_writing"]

        return {
            "current_step": "code_writer_done",
            "steps_completed": steps,
            "generated_code": generated_code,
            "code_out": cells,
            "messages": [
                AIMessage(
                    content="Training pipeline cell generated and executed."
                )
            ],
        }
