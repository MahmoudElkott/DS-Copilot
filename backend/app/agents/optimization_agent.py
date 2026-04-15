# backend/app/agents/optimization_agent.py
"""
Optimization Agent — performs hyperparameter tuning and model optimization.
Uses GridSearchCV/RandomizedSearchCV, cross-validation, and feature importance.
"""
import json
import logging

from langchain_core.messages import HumanMessage, AIMessage
from app.core.llm_router import llm_router
from app.core.executor import create_executor
from app.core.harness import HarnessEngine
from app.utils.helpers import extract_code, safe_json_parse

logger = logging.getLogger(__name__)


class OptimizationAgent:
    """Agent that optimizes model hyperparameters."""

    NAME = "optimization"

    @staticmethod
    async def run(state: dict) -> dict:
        logger.info("[Agent] ⚡ Optimization starting...")

        model = llm_router.get_model(task_type="optimization")
        dataset_info = state.get("dataset_info", {})
        model_selection = state.get("model_selection_result", {})
        training_result = state.get("training_result", {})

        task_type = model_selection.get("task_type", "classification")
        target_col = model_selection.get("target_column", None)
        recommended_models = model_selection.get("recommended_models", [])

        prompt = f"""
You are an ML optimization expert. Write Python code to optimize the best model.

TASK TYPE: {task_type}
TARGET COLUMN: {target_col}
MODELS TRAINED: {json.dumps(recommended_models, indent=2, default=str)}
PREVIOUS RESULTS: {json.dumps(training_result, indent=2, default=str)}
DATASET INFO: {json.dumps(dataset_info, indent=2, default=str)}

CLEANED DATA PATH: data/processed/cleaned_data.csv

Write complete Python code that:
1. Loads the cleaned dataset
2. Loads the best model from 'output/models/best_model.pkl'
3. Performs hyperparameter tuning using RandomizedSearchCV:
   - Define a comprehensive parameter grid
   - Use 5-fold cross-validation
   - Optimize for the primary metric (accuracy for classification, r2 for regression)
   - n_iter=20 for RandomizedSearchCV
4. Evaluates the optimized model vs the original
5. Performs feature importance analysis:
   - Use model's feature_importances_ if available
   - Otherwise use permutation importance
   - Save feature importance plot to 'output/figures/feature_importance.png'
6. Saves the optimized model to 'output/models/optimized_model.pkl'
7. Saves optimization results to 'output/reports/optimization_results.json'
8. Prints a JSON summary as the LAST line with:
   - best_params
   - best_score (CV score)
   - improvement_pct (vs original)
   - top_features (list of top 10 features)
   - original_score
   - optimized_score

IMPORTANT:
- Include ALL imports at the top
- Use try/except for robustness
- Create directories with os.makedirs(..., exist_ok=True)
- Handle both classification and regression appropriately
- Use joblib for model saving/loading
- Close all matplotlib figures after saving
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
            step_name="optimization",
            max_retries=3,
        )

        optimization_result = {}
        if result.success:
            lines = result.stdout.strip().split("\n")
            for line in reversed(lines):
                parsed = safe_json_parse(line)
                if parsed is not None:
                    optimization_result = parsed
                    break
            if not optimization_result:
                optimization_result = {"stdout": result.stdout[:1000]}

        return {
            "optimization_result": optimization_result,
            "current_step": "optimization_done",
            "steps_completed": state.get("steps_completed", []) + ["optimization"],
            "generated_code": {
                **state.get("generated_code", {}),
                "optimization": code,
            },
            "harness_reports": state.get("harness_reports", []) + [report.__dict__],
            "messages": [AIMessage(
                content=f"⚡ Optimization complete! "
                        f"Best score: {optimization_result.get('best_score', 'N/A')}, "
                        f"Improvement: {optimization_result.get('improvement_pct', 'N/A')}%"
            )],
        }
