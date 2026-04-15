# backend/app/agents/data_ingest_agent.py
"""
Data Ingest Agent — loads and understands the dataset.
Analyzes shape, types, nulls, duplicates, and suggests task type.
"""
import json
import logging

from langchain_core.messages import HumanMessage, AIMessage
from app.core.llm_router import llm_router
from app.core.executor import create_executor
from app.utils.helpers import extract_code, safe_json_parse

logger = logging.getLogger(__name__)


class DataIngestAgent:
    """Agent that loads and understands the dataset."""

    NAME = "data_ingest"

    @staticmethod
    async def run(state: dict) -> dict:
        logger.info("[Agent] 📥 Data Ingest starting...")

        model = llm_router.get_model(task_type="data_cleaning")

        analyze_code = f"""
import pandas as pd
import json
import os

# Try to load the dataset
filepath = r"{state['dataset_path']}"

if filepath.endswith('.csv'):
    df = pd.read_csv(filepath)
elif filepath.endswith(('.xls', '.xlsx')):
    df = pd.read_excel(filepath)
elif filepath.endswith('.json'):
    df = pd.read_json(filepath)
else:
    raise ValueError(f"Unsupported file type: {{filepath}}")

info = {{
    "shape": list(df.shape),
    "columns": list(df.columns),
    "dtypes": {{col: str(dtype) for col, dtype in df.dtypes.items()}},
    "null_counts": df.isnull().sum().to_dict(),
    "null_percentage": (df.isnull().sum() / len(df) * 100).round(2).to_dict(),
    "numeric_columns": list(df.select_dtypes(include='number').columns),
    "categorical_columns": list(df.select_dtypes(include='object').columns),
    "sample_data": df.head(3).to_dict(),
    "describe": df.describe().to_dict(),
    "duplicates": int(df.duplicated().sum()),
    "memory_usage_mb": round(df.memory_usage(deep=True).sum() / 1024**2, 2),
}}

print(json.dumps(info, default=str))
"""
        executor = create_executor(
            state["user_settings"].get("execution_env", "local")
        )
        result = await executor.execute(analyze_code)

        if result.success:
            dataset_info = safe_json_parse(result.stdout.strip(), {"error": "Failed to parse output"})
        else:
            dataset_info = {"error": result.stderr}

        # Ask LLM to analyze
        analysis_prompt = f"""
Analyze this dataset and provide insights:
{json.dumps(dataset_info, indent=2, default=str)}

Respond in JSON with:
- task_type: "classification" | "regression" | "clustering"
- target_column_suggestion: best column for target (or null)
- potential_issues: list of data quality issues
- recommended_steps: list of cleaning steps needed
"""
        response = await model.ainvoke([HumanMessage(content=analysis_prompt)])

        return {
            "dataset_info": dataset_info,
            "current_step": "data_ingest_done",
            "steps_completed": ["data_ingest"],
            "generated_code": {"data_ingest": analyze_code},
            "messages": [AIMessage(
                content=f"📥 Dataset loaded: {dataset_info.get('shape', 'unknown')} shape. "
                        f"Analysis: {response.content}"
            )],
        }
