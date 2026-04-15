# backend/app/agents/testing_agent.py
"""
Testing Agent — generates and runs pytest tests for the ML pipeline.
Uses TDD approach via harness engine.
"""
import json
import logging

from langchain_core.messages import HumanMessage, AIMessage
from app.core.llm_router import llm_router
from app.core.executor import create_executor
from app.core.harness import HarnessEngine
from app.utils.helpers import extract_code, safe_json_parse

logger = logging.getLogger(__name__)


class TestingAgent:
    """Agent that generates and runs tests for the pipeline."""

    NAME = "testing"

    @staticmethod
    async def run(state: dict) -> dict:
        logger.info("[Agent] 🧪 Testing starting...")

        model = llm_router.get_model(task_type="testing")
        dataset_info = state.get("dataset_info", {})
        model_selection = state.get("model_selection_result", {})
        training_result = state.get("training_result", {})
        training_code = state.get("generated_code", {}).get("code_writing", "")

        task_type = model_selection.get("task_type", "classification")
        target_col = model_selection.get("target_column", None)

        prompt = f"""
You are a senior QA engineer specializing in ML testing.
Write comprehensive pytest-style tests for this ML pipeline.

TASK TYPE: {task_type}
TARGET COLUMN: {target_col}
DATASET INFO: {json.dumps(dataset_info, indent=2, default=str)}
TRAINING RESULTS: {json.dumps(training_result, indent=2, default=str)}

CLEANED DATA PATH: data/processed/cleaned_data.csv
MODEL PATH: output/models/best_model.pkl

Write a COMPLETE standalone Python test script that:
1. Test data loading:
   - Verify cleaned_data.csv exists and loads correctly
   - Verify expected columns exist
   - Verify no null values in critical columns
   - Verify data types are correct

2. Test model:
   - Verify best_model.pkl exists and loads
   - Verify model can make predictions
   - Verify prediction shape matches input shape
   - Verify predictions are in valid range

3. Test pipeline integrity:
   - Verify train/test split ratios
   - Verify model performance is above baseline
   - For classification: accuracy > 0.5 (better than random)
   - For regression: R² > 0 (better than mean prediction)

4. Test edge cases:
   - Single row prediction
   - Prediction with missing values handling

IMPORTANT:
- Use pytest
- Run tests at the end with: pytest.main([__file__, '-v', '--tb=short'])
- Print a JSON summary of test results as the LAST line
- Include all imports
- Don't import from the training code — reload everything fresh
"""
        response = await model.ainvoke([HumanMessage(content=prompt)])
        test_code = extract_code(response.content)

        # Execute tests with harness
        executor = create_executor(
            state["user_settings"].get("execution_env", "local")
        )
        harness = HarnessEngine(executor, llm_router)
        result, report = await harness.execute_with_healing(
            code=test_code,
            step_name="testing",
            max_retries=2,
        )

        testing_result = {}
        if result.success:
            # Parse test output
            passed = result.stdout.count(" PASSED")
            failed = result.stdout.count(" FAILED")
            testing_result = {
                "tests_passed": passed,
                "tests_failed": failed,
                "total_tests": passed + failed,
                "success_rate": round(passed / max(passed + failed, 1) * 100, 1),
                "stdout": result.stdout[:2000],
            }
            report.tests_passed = passed
            report.tests_failed = failed
        else:
            testing_result = {
                "tests_passed": 0,
                "tests_failed": 0,
                "error": result.stderr[:1000],
            }

        return {
            "testing_result": testing_result,
            "current_step": "testing_done",
            "steps_completed": state.get("steps_completed", []) + ["testing"],
            "generated_code": {
                **state.get("generated_code", {}),
                "testing": test_code,
            },
            "harness_reports": state.get("harness_reports", []) + [report.__dict__],
            "messages": [AIMessage(
                content=f"🧪 Testing complete! "
                        f"Passed: {testing_result.get('tests_passed', 0)}, "
                        f"Failed: {testing_result.get('tests_failed', 0)}, "
                        f"Success rate: {testing_result.get('success_rate', 0)}%"
            )],
        }
