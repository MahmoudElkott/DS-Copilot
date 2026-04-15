# backend/app/agents/model_selection_agent.py
"""
Model Selection Agent — analyzes dataset characteristics
and recommends the best ML models for the task.
"""
import json
import logging

from langchain_core.messages import HumanMessage, AIMessage
from app.core.llm_router import llm_router
from app.utils.helpers import extract_code, safe_json_parse

logger = logging.getLogger(__name__)


class ModelSelectionAgent:
    """Agent that selects the best ML models for the dataset."""

    NAME = "model_selection"

    @staticmethod
    async def run(state: dict) -> dict:
        logger.info("[Agent] 🤖 Model Selection starting...")

        model = llm_router.get_model(task_type="model_selection")
        dataset_info = state.get("dataset_info", {})
        eda_result = state.get("eda_result", {})
        cleaning_result = state.get("cleaning_result", {})

        prompt = f"""
You are a senior ML engineer. Analyze the dataset and recommend the best models.

DATASET INFO:
{json.dumps(dataset_info, indent=2, default=str)}

EDA FINDINGS:
{json.dumps(eda_result, indent=2, default=str)}

CLEANING SUMMARY:
{json.dumps(cleaning_result, indent=2, default=str)}

Based on this analysis, respond in JSON with:
{{
    "task_type": "classification" | "regression" | "clustering",
    "target_column": "column_name or null",
    "recommended_models": [
        {{
            "name": "model_name",
            "class": "sklearn.ensemble.RandomForestClassifier",
            "reason": "why this model is suitable",
            "priority": 1,
            "hyperparameters": {{"param": "value"}}
        }}
    ],
    "baseline_model": "model_name",
    "evaluation_metrics": ["accuracy", "f1_score", "..."],
    "cross_validation_strategy": "stratified_kfold",
    "feature_engineering_suggestions": ["suggestion1", "..."],
    "warnings": ["any warnings about the data"]
}}

RULES:
- Recommend 3-5 models ranked by expected performance
- Include at least one simple baseline (LogisticRegression or LinearRegression)
- Include at least one ensemble method
- Include at least one boosting method (XGBoost/LightGBM)
- Consider dataset size, dimensionality, and feature types
- Be specific about hyperparameters to try
"""
        response = await model.ainvoke([HumanMessage(content=prompt)])
        model_selection_result = safe_json_parse(response.content, {
            "task_type": "classification",
            "recommended_models": [],
            "raw_response": response.content,
        })

        return {
            "model_selection_result": model_selection_result,
            "current_step": "model_selection_done",
            "steps_completed": state.get("steps_completed", []) + ["model_selection"],
            "generated_code": {
                **state.get("generated_code", {}),
                "model_selection": f"# Model Selection Result (LLM Analysis)\n# {json.dumps(model_selection_result, indent=2, default=str)}",
            },
            "messages": [AIMessage(
                content=f"🤖 Model selection complete! "
                        f"Task type: {model_selection_result.get('task_type', 'unknown')}. "
                        f"Recommended models: {[m.get('name', '?') for m in model_selection_result.get('recommended_models', [])]}. "
                        f"Baseline: {model_selection_result.get('baseline_model', 'N/A')}"
            )],
        }
