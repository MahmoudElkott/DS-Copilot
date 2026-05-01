"""Scientific Critic Agent — evaluates model results for scientific validity."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict

from langchain_core.messages import AIMessage, HumanMessage

from app.infrastructure.llm_router import llm_router
from app.utils.helpers import safe_json_parse, compact_json_for_prompt

logger = logging.getLogger(__name__)


class CriticAgent:
    NAME = "critic"
    QUALITY_THRESHOLD = 0.7

    @staticmethod
    async def run(state: dict) -> dict:
        logger.info("[Agent] Scientific Critic evaluating results...")

        user_settings = state.get("user_settings", {})
        model = llm_router.get_model(
            task_type="model_selection",
            provider_override=user_settings.get("llm_provider"),
            model_override=user_settings.get("model_name"),
            runtime_settings=user_settings,
        )

        training_result = state.get("training_result", {})
        testing_result = state.get("testing_result", {})
        model_selection = state.get("model_selection_result", {})
        dataset_info = state.get("dataset_info", {})

        threshold = CriticAgent.QUALITY_THRESHOLD
        prompt = f"""You are a rigorous ML scientist performing a final review of model results.

Training Result:
{compact_json_for_prompt(training_result, max_chars=2000)}

Testing Result:
{compact_json_for_prompt(testing_result, max_chars=2000)}

Model Selection:
{compact_json_for_prompt(model_selection, max_chars=1500)}

Dataset Info:
{compact_json_for_prompt(dataset_info, max_chars=1000)}

Evaluate:
1. Is the best accuracy/R2 score above {threshold}?
2. Is there evidence of data leakage (test accuracy >> train accuracy)?
3. Are the chosen metrics appropriate for the task type?
4. Is there suspicious overfitting (train >>> test)?
5. Are baseline comparisons valid?

Respond in JSON:
{{
    "verdict": "pass" or "fail",
    "score": 0.0 to 1.0,
    "issues": ["issue1", ...],
    "recommendations": ["recommendation1", ...],
    "scientific_reasoning": "A paragraph explaining the scientific assessment."
}}"""

        response = await model.ainvoke([HumanMessage(content=prompt)])
        critic_result = safe_json_parse(
            response.content,
            {
                "verdict": "pass",
                "score": 0.5,
                "issues": [],
                "recommendations": [],
                "scientific_reasoning": response.content,
            },
        )

        verdict = critic_result.get("verdict", "pass")

        steps = list(state.get("steps_completed", []))
        if "critic" not in steps:
            steps = steps + ["critic"]

        return {
            "critic_result": critic_result,
            "current_step": "critic_done" if verdict == "pass" else "critic_failed",
            "steps_completed": steps,
            "messages": [
                AIMessage(
                    content=(
                        f"Scientific Critic: {verdict.upper()}. "
                        f"Score: {critic_result.get('score', 'N/A')}. "
                        f"{str(critic_result.get('scientific_reasoning', ''))[:300]}"
                    )
                )
            ],
        }
