# backend/app/agents/eda_agent.py
"""
EDA Agent — performs Exploratory Data Analysis.
Generates visualizations, statistical summaries, correlation analysis.
"""
import os
import json
import logging
import base64

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from app.infrastructure.llm_router import llm_router
from app.infrastructure.utils import CodeSplitter
from app.infrastructure.executor import create_executor
from app.infrastructure.paths import GlobalPathManager
from app.utils.helpers import extract_code, safe_json_parse, compact_json_for_prompt

logger = logging.getLogger(__name__)


class EDAAgent:
    """Agent that performs Exploratory Data Analysis using Modular Cell Architecture."""

    NAME = "eda"

    @staticmethod
    async def run(state: dict) -> dict:
        logger.info("[Agent] 📊 EDA starting...")

        user_settings = state.get("user_settings", {})
        model = llm_router.get_model(
            task_type="code_writing",
            provider_override=user_settings.get("llm_provider"),
            model_override=user_settings.get("model_name"),
            runtime_settings=user_settings,
        )
        dataset_info = state.get("dataset_info", {})
        from app.agent.tools.file_handler import FileHandler
        dataset_path = FileHandler.get_dataset_path(state)
        plots_dir = FileHandler.get_directory("plots")

        system_prompt = f"""
You are a Lead Data Science Engineer performing Exploratory Data Analysis.
You MUST generate a minimum of 4-5 distinct code cells, each tagged with exactly this format:
### CELL: [Name]

Requested Visuals:
1. Numerical distributions (Histograms).
2. Categorical counts (Bar charts).
3. Feature dependencies (Seaborn Heatmap).
4. Anomaly detection (Boxplots).
5. (Optional) Time-series or Pairplots if relevant.

IMPORTANT:
- Load the dataset strictly from: {dataset_path}
- Ensure all plotting code uses `import matplotlib; matplotlib.use('Agg')` BEFORE importing pyplot.
- Save ALL artifacts/images to the directory: {plots_dir}
- For each code cell, you MUST print a Markdown summary explaining the statistical significance of the chart using print().
- Output raw Python code only, separated by the cell delimiters. Do not output markdown except inside print() statements and cell delimiters.
"""
        
        user_message = f"""
Dataset Info:
{compact_json_for_prompt(dataset_info)}

Perform EDA on: {dataset_path}
"""
        messages = [
            SystemMessage(content=system_prompt.strip()),
            HumanMessage(content=user_message.strip())
        ]
        
        response = await model.ainvoke(messages)
        raw_code = response.content
        
        cells = CodeSplitter.parse_cells(raw_code, stage="eda")
        full_code = "\n\n".join([cell["content"] for cell in cells])
        
        executor = create_executor(
            user_settings.get("execution_env", "local"),
            session_id=state["session_id"],
            python_interpreter=user_settings.get("python_interpreter"),
            e2b_api_key=user_settings.get("e2b_api_key"),
        )
        
        context_config = None
        if hasattr(executor, "sandbox_dir"):
            context_config = GlobalPathManager.get_context_config(
                executor.sandbox_dir, dataset_path
            )
            
        timeout_seconds = int(user_settings.get("execution_timeout", 120))
        exec_result = await executor.execute(full_code, timeout=timeout_seconds, context_config=context_config)
        
        images = {}
        if os.path.exists(plots_dir):
            for filename in os.listdir(plots_dir):
                if filename.lower().endswith((".png", ".jpg", ".jpeg")):
                    file_path = os.path.join(plots_dir, filename)
                    try:
                        with open(file_path, "rb") as f:
                            b64 = base64.b64encode(f.read()).decode("utf-8")
                            images[filename] = f"data:image/png;base64,{b64}"
                    except Exception as e:
                        logger.error(f"Error reading image {filename}: {e}")
        
        eda_result = {
            "success": exec_result.success,
            "stdout": exec_result.stdout,
            "stderr": exec_result.stderr,
            "images": images
        }

        generated_code = dict(state.get("generated_code", {}))
        generated_code["eda"] = full_code
        
        existing_cells = state.get("code_out", [])
        # In case we retry EDA, we don't want duplicate EDA cells. Filter out old EDA cells.
        new_code_out = [c for c in existing_cells if c.get("metadata", {}).get("stage") != "eda"] + cells
        
        steps = state.get("steps_completed", [])
        if "eda" not in steps:
            steps = steps + ["eda"]

        return {
            "eda_result": eda_result,
            "visualization_payload": {
                **state.get("visualization_payload", {}),
                "eda_output": exec_result.stdout,
                "eda_images": images
            },
            "generated_code": generated_code,
            "code_out": new_code_out,
            "current_step": "eda_done",
            "steps_completed": steps,
            "messages": [AIMessage(content="📊 EDA completed with modular cells.")],
        }
