# backend/app/agents/eda_agent.py
"""
EDA Agent — performs Exploratory Data Analysis.
Generates visualizations, statistical summaries, correlation analysis.
"""
import json
import logging

from langchain_core.messages import HumanMessage, AIMessage
from app.core.llm_router import llm_router
from app.core.executor import create_executor
from app.core.harness import HarnessEngine
from app.utils.helpers import extract_code, safe_json_parse

logger = logging.getLogger(__name__)


class EDAAgent:
    """Agent that performs Exploratory Data Analysis."""

    NAME = "eda"

    @staticmethod
    async def run(state: dict) -> dict:
        logger.info("[Agent] 📊 EDA starting...")

        model = llm_router.get_model(task_type="eda")
        dataset_info = state.get("dataset_info", {})

        prompt = f"""
You are an expert data scientist. Write Python code for comprehensive EDA.

DATASET INFO:
{json.dumps(dataset_info, indent=2, default=str)}

CLEANED DATA PATH: data/processed/cleaned_data.csv

Write complete Python code that:
1. Loads the cleaned dataset
2. Generates distribution plots for all numeric columns
3. Correlation heatmap
4. Box plots for numeric columns
5. Value counts for categorical columns
6. Pair plot for top 5 most correlated features
7. Missing value visualization
8. Save ALL plots to 'output/figures/' directory
9. Print a JSON summary of key findings

Use matplotlib and seaborn. Save figures, don't show them.
Use plt.savefig() with dpi=150 and bbox_inches='tight'.

IMPORTANT:
- Use pandas, matplotlib, seaborn
- Create 'output/figures/' directory if it doesn't exist
- Make it robust with try/except
- Print the summary as the LAST line as valid JSON
- Include all imports at the top
- Close all figures after saving (plt.close())
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
            step_name="eda",
            max_retries=3,
        )

        eda_result = {}
        if result.success:
            lines = result.stdout.strip().split("\n")
            for line in reversed(lines):
                parsed = safe_json_parse(line)
                if parsed is not None:
                    eda_result = parsed
                    break
            if not eda_result:
                eda_result = {"stdout": result.stdout[:1000]}

        return {
            "eda_result": eda_result,
            "current_step": "eda_done",
            "steps_completed": state.get("steps_completed", []) + ["eda"],
            "generated_code": {
                **state.get("generated_code", {}),
                "eda": code,
            },
            "harness_reports": state.get("harness_reports", []) + [report.__dict__],
            "messages": [AIMessage(
                content=f"📊 EDA complete! Generated visualizations. "
                        f"Findings: {json.dumps(eda_result, default=str)[:500]}"
            )],
        }
