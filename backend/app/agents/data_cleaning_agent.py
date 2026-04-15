# backend/app/agents/data_cleaning_agent.py
"""
Data Cleaning Agent — cleans and preprocesses data.
Handles missing values, duplicates, outliers, type fixes, encoding.
"""
import json
import logging

from langchain_core.messages import HumanMessage, AIMessage
from app.core.llm_router import llm_router
from app.core.executor import create_executor
from app.core.harness import HarnessEngine
from app.utils.helpers import extract_code, safe_json_parse

logger = logging.getLogger(__name__)


class DataCleaningAgent:
    """Agent that cleans and preprocesses data."""

    NAME = "data_cleaning"

    @staticmethod
    async def run(state: dict) -> dict:
        logger.info("[Agent] 🧹 Data Cleaning starting...")

        model = llm_router.get_model(task_type="data_cleaning")
        dataset_info = state.get("dataset_info", {})

        prompt = f"""
You are an expert data engineer. Write Python code to clean this dataset.

DATASET INFO:
{json.dumps(dataset_info, indent=2, default=str)}

FILE PATH: {state['dataset_path']}

Write complete Python code that:
1. Loads the dataset
2. Handles missing values (appropriate strategy per column)
3. Removes duplicates
4. Fixes data types
5. Handles outliers (IQR method for numeric columns)
6. Encodes categorical variables if needed
7. Saves cleaned dataset to 'data/processed/cleaned_data.csv'
8. Prints a JSON summary of changes made

IMPORTANT:
- Use pandas
- Make it robust with try/except
- Print the summary as the LAST line as valid JSON
- Include all imports at the top
"""
        response = await model.ainvoke([HumanMessage(content=prompt)])
        code = extract_code(response.content)

        # Execute with harness (self-healing)
        executor = create_executor(
            state["user_settings"].get("execution_env", "local")
        )
        harness = HarnessEngine(executor, llm_router)
        result, report = await harness.execute_with_healing(
            code=code,
            step_name="data_cleaning",
            max_retries=3,
        )

        cleaning_result = {}
        if result.success:
            try:
                # Get last line as JSON
                lines = result.stdout.strip().split("\n")
                for line in reversed(lines):
                    parsed = safe_json_parse(line)
                    if parsed is not None:
                        cleaning_result = parsed
                        break
            except Exception:
                cleaning_result = {"stdout": result.stdout}

        return {
            "cleaning_result": cleaning_result,
            "current_step": "cleaning_done",
            "steps_completed": state.get("steps_completed", []) + ["data_cleaning"],
            "generated_code": {
                **state.get("generated_code", {}),
                "data_cleaning": code,
            },
            "harness_reports": state.get("harness_reports", []) + [report.__dict__],
            "messages": [AIMessage(
                content=f"🧹 Data cleaned! {json.dumps(cleaning_result, default=str)[:500]}"
            )],
        }
