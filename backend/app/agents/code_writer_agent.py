# backend/app/agents/code_writer_agent.py
"""
Code Writer Agent — generates the complete ML training pipeline.
Produces runnable Python code for data loading, training, evaluation, and model saving.
"""
import json
import logging

from langchain_core.messages import HumanMessage, AIMessage
from app.core.llm_router import llm_router
from app.core.executor import create_executor
from app.core.harness import HarnessEngine
from app.utils.helpers import extract_code, safe_json_parse

logger = logging.getLogger(__name__)


class CodeWriterAgent:
    """Agent that generates the complete training pipeline code."""

    NAME = "code_writer"

    @staticmethod
    async def run(state: dict) -> dict:
        logger.info("[Agent] ✍️ Code Writer starting...")

        model = llm_router.get_model(task_type="code_writing")
        dataset_info = state.get("dataset_info", {})
        model_selection = state.get("model_selection_result", {})
        cleaning_code = state.get("generated_code", {}).get("data_cleaning", "")

        task_type = model_selection.get("task_type", "classification")
        target_col = model_selection.get("target_column", None)
        recommended_models = model_selection.get("recommended_models", [])
        eval_metrics = model_selection.get("evaluation_metrics", ["accuracy"])

        prompt = f"""
You are a senior ML engineer. Write a COMPLETE Python training pipeline.

DATASET INFO:
{json.dumps(dataset_info, indent=2, default=str)}

TASK TYPE: {task_type}
TARGET COLUMN: {target_col}
MODELS TO TRAIN: {json.dumps(recommended_models, indent=2, default=str)}
EVALUATION METRICS: {eval_metrics}

CLEANED DATA PATH: data/processed/cleaned_data.csv

Write complete Python code that:
1. Loads the cleaned dataset from 'data/processed/cleaned_data.csv'
2. Separates features (X) and target (y) using target column: '{target_col}'
3. Splits data into train/test sets (80/20, random_state=42)
4. Trains EACH recommended model with specified hyperparameters
5. Evaluates each model on test set using the specified metrics
6. Generates a comparison table of results
7. Saves the best model using joblib to 'output/models/best_model.pkl'
8. Saves the comparison results to 'output/reports/model_comparison.json'
9. Prints a JSON summary of all results as the LAST line

IMPORTANT RULES:
- Include ALL imports at the top
- Use try/except for robustness
- Handle both classification and regression metrics appropriately
- For classification: accuracy, precision, recall, f1_score, classification_report
- For regression: mse, rmse, r2_score, mae
- Use sklearn.model_selection.cross_val_score for cross-validation
- Create output directories if they don't exist
- Use os.makedirs(..., exist_ok=True)
- Print the final JSON summary as the LAST line of stdout
- The JSON summary must include: model_name, metrics, training_time for each model
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
            step_name="code_writing",
            max_retries=3,
        )

        training_result = {}
        if result.success:
            lines = result.stdout.strip().split("\n")
            for line in reversed(lines):
                parsed = safe_json_parse(line)
                if parsed is not None:
                    training_result = parsed
                    break
            if not training_result:
                training_result = {"stdout": result.stdout[:1000]}

        return {
            "training_result": training_result,
            "current_step": "code_writing_done",
            "steps_completed": state.get("steps_completed", []) + ["code_writing"],
            "generated_code": {
                **state.get("generated_code", {}),
                "code_writing": code,
            },
            "harness_reports": state.get("harness_reports", []) + [report.__dict__],
            "messages": [AIMessage(
                content=f"✍️ Training pipeline complete! "
                        f"Results: {json.dumps(training_result, default=str)[:500]}"
            )],
        }
