"""Unified DS-Copilot orchestrator and LangGraph factory."""

from __future__ import annotations

import asyncio
import contextvars
import json
import logging
from typing import Any, Awaitable, Callable, Dict

from langchain_core.messages import AIMessage
from langgraph.graph import END, StateGraph

from app.agent.core.executor import AgentExecutor
from app.agents.code_writer_agent import CodeWriterAgent
from app.agents.critic_agent import CriticAgent
from app.agents.data_cleaning_agent import DataCleaningAgent
from app.agents.data_ingest_agent import DataIngestAgent
from app.agents.documentation_agent import DocumentationAgent
from app.agents.eda_agent import EDAAgent
from app.agents.model_selection_agent import ModelSelectionAgent
from app.agents.optimization_agent import OptimizationAgent
from app.agents.testing_agent import TestingAgent
from app.config import settings
from app.infrastructure.executor import create_executor
from app.infrastructure.file_manager import FileManager
from app.infrastructure.git_manager import GitManager
from app.infrastructure.memory import memory
from app.models.schemas import AgentStateModel, InternalPipelineModel
from app.utils.helpers import safe_json_parse

logger = logging.getLogger(__name__)

ResponseCallback = Callable[[Dict[str, Any]], Awaitable[None]]

_CURRENT_RESPONSE_STRATEGY: contextvars.ContextVar["ResponseStrategy | None"] = contextvars.ContextVar(
    "current_response_strategy",
    default=None,
)
_CURRENT_MESSAGE_CALLBACK: contextvars.ContextVar[ResponseCallback | None] = contextvars.ContextVar(
    "current_message_callback",
    default=None,
)


class ResponseStrategy:
    """Base strategy for orchestrator responses."""

    def __init__(self) -> None:
        self._sequence_id = 0

    def _prepare_payload(self, message: Dict[str, Any]) -> Dict[str, Any]:
        payload = dict(message)
        metadata = dict(payload.get("metadata") or {})
        self._sequence_id += 1
        metadata.setdefault("sequence_id", self._sequence_id)
        payload["metadata"] = metadata
        return payload

    async def emit(self, message: Dict[str, Any]) -> None:
        raise NotImplementedError

    async def on_start(self, session_id: str, state: Dict[str, Any]) -> None:
        await self.emit(
            {
                "type": "status",
                "agent": "orchestrator",
                "content": f"Pipeline graph initiated for {session_id}",
                "metadata": {"action": "graph_start", "session_id": session_id},
            }
        )

    async def on_complete(self, session_id: str, final_state: Dict[str, Any]) -> None:
        await self.emit(
            {
                "type": "status",
                "agent": "orchestrator",
                "content": "Pipeline execution completed.",
                "metadata": {
                    "action": "graph_end",
                    "final_step": final_state.get("current_step"),
                    "session_id": session_id,
                },
            }
        )

    async def on_error(self, session_id: str, error: str) -> None:
        await self.emit(
            {
                "type": "error",
                "agent": "orchestrator",
                "content": f"Critical orchestrator failure: {error}",
                "metadata": {"action": "graph_error", "session_id": session_id},
            }
        )


class CallbackResponseStrategy(ResponseStrategy):
    """Strategy that forwards messages to a callback."""

    def __init__(self, callback: ResponseCallback | None) -> None:
        super().__init__()
        self.callback = callback

    async def emit(self, message: Dict[str, Any]) -> None:
        if self.callback is None:
            return
        await self.callback(self._prepare_payload(message))


class CollectingResponseStrategy(ResponseStrategy):
    """Strategy that stores messages for later inspection."""

    def __init__(self) -> None:
        super().__init__()
        self.events: list[Dict[str, Any]] = []

    async def emit(self, message: Dict[str, Any]) -> None:
        self.events.append(self._prepare_payload(message))


AgentState = InternalPipelineModel


def _resolve_message_callback() -> ResponseCallback | None:
    return _CURRENT_MESSAGE_CALLBACK.get()


def _validate_state(state: Dict[str, Any]) -> InternalPipelineModel:
    return InternalPipelineModel.model_validate(state)


def _append_step(state: Dict[str, Any], step_key: str) -> list[str]:
    steps = list(state.get("steps_completed", []))
    if step_key not in steps:
        steps.append(step_key)
    return steps


def _append_error(state: Dict[str, Any], step_key: str, error: str) -> list[Dict[str, str]]:
    errors = list(state.get("errors", []))
    errors.append({"step": step_key, "error": error})
    return errors


def _extract_last_json_line(stdout: str) -> Dict[str, Any]:
    if not stdout:
        return {}
    lines = stdout.strip().splitlines()
    for line in reversed(lines):
        parsed = safe_json_parse(line)
        if isinstance(parsed, dict):
            return parsed
    parsed = safe_json_parse(stdout)
    return parsed if isinstance(parsed, dict) else {}


async def _extract_weights_from_artifacts(executor) -> Dict[str, Any]:
    probe_code = """
import json
import os

import joblib
import numpy as np

weights = {"kind": "unknown", "shape": [], "values": []}
model_path = "output/models/best_model.pkl"

if os.path.exists(model_path):
    model = joblib.load(model_path)

    if hasattr(model, "coef_"):
        arr = np.array(model.coef_)
        weights = {
            "kind": "coef",
            "shape": list(arr.shape),
            "matrix": arr.tolist(),
        }
    elif hasattr(model, "feature_importances_"):
        arr = np.array(model.feature_importances_)
        weights = {
            "kind": "feature_importances",
            "shape": list(arr.shape),
            "values": arr.tolist(),
        }
    elif hasattr(model, "estimators_") and len(getattr(model, "estimators_", [])) > 0:
        first_estimator = model.estimators_[0]
        if hasattr(first_estimator, "coef_"):
            arr = np.array(first_estimator.coef_)
            weights = {
                "kind": "estimator_coef",
                "shape": list(arr.shape),
                "matrix": arr.tolist(),
            }

print(json.dumps(weights, default=str))
"""
    probe_result = await executor.execute(probe_code, timeout=60)
    if not probe_result.success:
        return {}
    parsed = _extract_last_json_line(probe_result.stdout)
    return parsed if isinstance(parsed, dict) else {}


async def _run_agent_node(agent_cls, state: AgentState, step_key: str) -> dict:
    _validate_state(state)
    max_retries = 3
    timeout_seconds = 120
    callback = _resolve_message_callback()

    if callback is not None:
        await callback({
            "type": "agent_action",
            "agent": step_key,
            "content": f"{step_key} starting",
            "metadata": {"status": "running", "stage": step_key, "step": step_key},
        })

    for attempt in range(max_retries):
        try:
            result = await asyncio.wait_for(agent_cls.run(state), timeout=timeout_seconds)
            if step_key not in result.get("steps_completed", []):
                result["steps_completed"] = _append_step(state, step_key)
            memory.save_message(
                session_id=state["session_id"],
                role="agent",
                content=(
                    result["messages"][0].content
                    if result.get("messages")
                    else f"{step_key} completed"
                ),
                agent_name=agent_cls.NAME,
            )
            if callback is not None:
                await callback({
                    "type": "status",
                    "agent": step_key,
                    "content": f"{step_key} complete",
                    "metadata": {
                        "step": step_key,
                        "step_complete": True,
                        "stages": step_key,
                        "steps_completed": result.get("steps_completed", []),
                    },
                })
            return result
        except asyncio.TimeoutError:
            logger.error(
                "[Orchestrator] %s failed: timeout after %s seconds (attempt %d/%d)",
                step_key,
                timeout_seconds,
                attempt + 1,
                max_retries,
            )
            if attempt == max_retries - 1:
                return {
                    "errors": _append_error(state, step_key, f"Timeout after {timeout_seconds}s"),
                    "current_step": f"{step_key}_error",
                    "messages": [AIMessage(content=f"{step_key} failed: Timeout")],
                }
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "[Orchestrator] %s failed: %s (attempt %d/%d)",
                step_key,
                exc,
                attempt + 1,
                max_retries,
                exc_info=True,
            )
            if attempt == max_retries - 1:
                return {
                    "errors": _append_error(state, step_key, str(exc)),
                    "current_step": f"{step_key}_error",
                    "messages": [AIMessage(content=f"{step_key} failed after {max_retries} retries: {exc}")],
                }

    if callback is not None:
        await callback(
            {
                "type": "error",
                "agent": step_key,
                "content": f"{step_key} exhausted retries",
                "metadata": {"step": step_key},
            }
        )
    return {
        "errors": _append_error(state, step_key, f"{step_key} exhausted retries"),
        "current_step": f"{step_key}_error",
        "messages": [AIMessage(content=f"{step_key} failed after retries")],
    }


async def data_ingest_node(state: AgentState) -> dict:
    return await _run_agent_node(DataIngestAgent, state, "data_ingest")


async def data_cleaning_node(state: AgentState) -> dict:
    return await _run_agent_node(DataCleaningAgent, state, "data_cleaning")


async def eda_node(state: AgentState) -> dict:
    return await _run_agent_node(EDAAgent, state, "eda")


async def model_selection_node(state: AgentState) -> dict:
    return await _run_agent_node(ModelSelectionAgent, state, "model_selection")


async def code_writer_node(state: AgentState) -> dict:
    return await _run_agent_node(CodeWriterAgent, state, "code_writing")


async def execute_code_node(state: AgentState) -> dict:
    """Explicit code execution node. This blocks until execution fully completes."""
    validated = _validate_state(state)

    code = (validated.generated_code or {}).get("code_writing", "")
    if not code.strip():
        error = "No generated code found for code_writing step."
        retry_count = validated.retry_count + 1
        return {
            "retry_count": retry_count,
            "last_execution_error": error,
            "errors": _append_error(state, "execute_code", error),
            "execution_result": {
                "success": False,
                "exit_code": 1,
                "stdout": "",
                "stderr": error,
            },
            "current_step": "execution_failed",
            "messages": [AIMessage(content=f"Execution failed: {error}")],
        }

    executor = create_executor(
        validated.user_settings.get("execution_env", "local"),
        session_id=validated.session_id,
        python_interpreter=validated.user_settings.get("python_interpreter"),
        e2b_api_key=validated.user_settings.get("e2b_api_key"),
    )

    from app.infrastructure.paths import GlobalPathManager

    context_config = None
    if hasattr(executor, "sandbox_dir"):
        context_config = GlobalPathManager.get_context_config(
            executor.sandbox_dir, validated.dataset_path
        )

    timeout_seconds = int(validated.user_settings.get("execution_timeout", 120))
    result = await executor.execute(code, timeout=timeout_seconds, context_config=context_config)

    execution_result = {
        "success": result.success,
        "exit_code": result.exit_code,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "execution_time": result.execution_time,
        "files_created": result.files_created,
    }

    if not result.success or (result.exit_code is not None and result.exit_code != 0):
        retry_count = validated.retry_count + 1
        error_text = result.stderr or f"Execution failed with exit code {result.exit_code}"

        if retry_count >= validated.max_retries:
            return {
                "retry_count": retry_count,
                "last_execution_error": error_text,
                "errors": _append_error(state, "execute_code", error_text),
                "execution_result": execution_result,
                "current_step": "execution_error",
                "messages": [
                    AIMessage(
                        content=f"Execution failed after {validated.max_retries} retries. Error: {error_text}"
                    )
                ],
            }

        return {
            "retry_count": retry_count,
            "last_execution_error": error_text,
            "errors": _append_error(state, "execute_code", error_text),
            "execution_result": execution_result,
            "current_step": "execution_failed",
            "messages": [
                AIMessage(
                    content=(
                        "Execution failed. "
                        f"Retry {retry_count}/{validated.max_retries}. "
                        "Routing back to code_writer with stderr context."
                    )
                )
            ],
        }

    training_result = _extract_last_json_line(result.stdout)
    if not isinstance(training_result, dict):
        training_result = {}
    if not training_result:
        training_result = {"stdout_preview": result.stdout[-2000:]}

    model_weights = training_result.get("model_weights")
    if not isinstance(model_weights, dict) or not model_weights:
        try:
            model_weights = await _extract_weights_from_artifacts(executor)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Weight extraction probe failed: %s", exc)
            model_weights = {}

    if model_weights:
        training_result["model_weights"] = model_weights

    visualization_payload = dict(state.get("visualization_payload", {}))
    visualization_payload.update(
        {
            "model_weights": model_weights or {},
            "model_metrics": training_result.get("models", training_result.get("metrics", {})),
            "eda": state.get("eda_result", {}),
        }
    )

    return {
        "retry_count": validated.retry_count,
        "last_execution_error": "",
        "training_result": training_result,
        "execution_result": execution_result,
        "visualization_payload": visualization_payload,
        "current_step": "execution_done",
        "steps_completed": _append_step(state, "execute_code"),
        "messages": [
            AIMessage(
                content=(
                    "Code execution completed successfully. "
                    f"Exit code: {result.exit_code}, duration: {result.execution_time:.2f}s"
                )
            )
        ],
    }


async def testing_node(state: AgentState) -> dict:
    return await _run_agent_node(TestingAgent, state, "testing")


async def optimization_node(state: AgentState) -> dict:
    return await _run_agent_node(OptimizationAgent, state, "optimization")


async def critic_node(state: AgentState) -> dict:
    return await _run_agent_node(CriticAgent, state, "critic")


async def documentation_node(state: AgentState) -> dict:
    """Documentation + optional git commit."""
    try:
        _validate_state(state)

        if not state.get("project_dir"):
            file_manager = FileManager()
            state["project_dir"] = file_manager.create_project_structure(
                state.get("project_name", "ds-project")
            )

        result = await DocumentationAgent.run(state)
        memory.save_message(
            session_id=state["session_id"],
            role="agent",
            content=(
                result["messages"][0].content
                if result.get("messages")
                else "Documentation completed"
            ),
            agent_name=DocumentationAgent.NAME,
        )

        if settings.ENABLE_GIT and settings.GIT_AUTO_COMMIT and state.get("project_dir"):
            try:
                git = GitManager(state["project_dir"])
                git.commit(
                    f"DS-Copilot: Pipeline complete for {state.get('project_name', 'project')}"
                )
            except Exception as git_err:  # noqa: BLE001
                logger.warning("Git commit failed: %s", git_err)

        return result
    except Exception as exc:  # noqa: BLE001
        logger.error("[Orchestrator] Documentation failed: %s", exc, exc_info=True)
        return {
            "errors": _append_error(state, "documentation", str(exc)),
            "current_step": "documentation_error",
            "messages": [AIMessage(content=f"documentation failed: {exc}")],
        }


def should_do_eda(state: AgentState) -> str:
    cleaning_result = state.get("cleaning_result", {})
    current_file_path = cleaning_result.get("file_path") or state.get("dataset_path")
    if current_file_path:
        return "eda"
    return "model_selection"


def route_after_execution(state: AgentState) -> str:
    """Self-healing router after code execution."""
    execution_result = state.get("execution_result", {}) or {}
    if execution_result.get("success"):
        return "testing"

    retry_count = int(state.get("retry_count", 0))
    max_retries = int(state.get("max_retries", 3))
    if retry_count < max_retries:
        return "code_writer"

    return "documentation"


def route_after_testing(state: AgentState) -> str:
    testing_result = state.get("testing_result", {})
    if testing_result.get("tests_failed", 0) > testing_result.get("tests_passed", 0):
        logger.warning("[Orchestrator] Too many test failures - skipping optimization")
        return "documentation"
    return "critic"


def route_after_critic(state: AgentState) -> str:
    """Route after scientific critic evaluation."""
    critic_result = state.get("critic_result", {})
    if critic_result.get("verdict") == "fail":
        critic_retry = int(state.get("critic_retry_count", 0))
        if critic_retry < 2:
            return "model_selection"
        return "documentation"
    return "optimization"


def route_entry(state: AgentState) -> str:
    """Determine where to start/resume the pipeline."""
    steps = state.get("steps_completed", [])

    pipeline_order = [
        ("data_ingest", "data_ingest"),
        ("data_cleaning", "data_cleaning"),
        ("eda", "eda"),
        ("model_selection", "model_selection"),
        ("code_writing", "code_writer"),
        ("execute_code", "execute_code"),
        ("testing", "testing"),
        ("critic", "critic"),
        ("optimization", "optimization"),
        ("documentation", "documentation"),
    ]

    for step_key, node_name in pipeline_order:
        if step_key not in steps:
            logger.info("[Orchestrator] Starting/Resuming from: %s", node_name)
            return node_name

    return "documentation"


def build_pipeline_graph() -> StateGraph:
    """Build the LangGraph state graph for the full DS pipeline."""
    graph = StateGraph(InternalPipelineModel)

    graph.add_node("data_ingest", data_ingest_node)
    graph.add_node("data_cleaning", data_cleaning_node)
    graph.add_node("eda", eda_node)
    graph.add_node("model_selection", model_selection_node)
    graph.add_node("code_writer", code_writer_node)
    graph.add_node("execute_code", execute_code_node)
    graph.add_node("testing", testing_node)
    graph.add_node("optimization", optimization_node)
    graph.add_node("documentation", documentation_node)

    graph.add_node("start_router", lambda x: x)
    graph.set_entry_point("start_router")

    graph.add_conditional_edges(
        "start_router",
        route_entry,
        {
            "data_ingest": "data_ingest",
            "data_cleaning": "data_cleaning",
            "eda": "eda",
            "model_selection": "model_selection",
            "code_writer": "code_writer",
            "execute_code": "execute_code",
            "testing": "testing",
            "optimization": "optimization",
            "documentation": "documentation",
        },
    )

    graph.add_edge("data_ingest", "data_cleaning")
    graph.add_conditional_edges(
        "data_cleaning",
        should_do_eda,
        {
            "eda": "eda",
            "model_selection": "model_selection",
        },
    )
    graph.add_edge("eda", "model_selection")
    graph.add_edge("model_selection", "code_writer")
    graph.add_edge("code_writer", "execute_code")
    graph.add_conditional_edges(
        "execute_code",
        route_after_execution,
        {
            "testing": "testing",
            "code_writer": "code_writer",
            "documentation": "documentation",
        },
    )
    graph.add_conditional_edges(
        "testing",
        route_after_testing,
        {
            "optimization": "optimization",
            "documentation": "documentation",
        },
    )
    graph.add_edge("optimization", "documentation")
    graph.add_edge("documentation", END)

    return graph


def create_pipeline():
    graph = build_pipeline_graph()
    return graph.compile()


def create_initial_state(
    session_id: str,
    dataset_path: str,
    project_name: str = "ds-project",
    user_settings: dict | None = None,
) -> AgentState:
    """Create the initial state for a new pipeline run."""
    merged_settings = {
        "execution_env": settings.DEFAULT_EXECUTION_ENV.value,
        "llm_provider": settings.DEFAULT_LLM_PROVIDER.value,
        "model_name": settings.DEFAULT_MODEL,
        "python_interpreter": settings.DEFAULT_PYTHON_INTERPRETER,
    }
    if user_settings:
        merged_settings.update(user_settings)

    candidate = AgentStateModel(
        session_id=session_id,
        project_name=project_name,
        project_dir="",
        messages=[],
        user_settings=merged_settings,
        dataset_path=dataset_path,
        dataset_info={},
        cleaning_result={},
        eda_result={},
        feature_engineering_result={},
        model_selection_result={},
        training_result={},
        testing_result={},
        optimization_result={},
        execution_result={},
        generated_code={},
        generated_notebooks={},
        current_step="init",
        steps_completed=[],
        errors=[],
        should_do_eda=True,
        should_compare_models=True,
        retry_count=0,
        max_retries=max(1, int(settings.MAX_RETRIES)),
        last_execution_error="",
        harness_reports=[],
        visualization_payload={},
        final_report={},
    )
    return candidate.model_dump(mode="python")


class DSOrchestrator:
    """Unified orchestrator for REST and WebSocket execution."""

    def __init__(
        self,
        message_callback: ResponseCallback | None = None,
    ) -> None:
        self.message_callback = message_callback
        self.graph = create_pipeline()

    async def _dispatch_event(self, message: Dict[str, Any]) -> None:
        strategy = _CURRENT_RESPONSE_STRATEGY.get()
        if strategy is None:
            return
        await strategy.emit(message)

    async def run(
        self,
        state: Dict[str, Any],
        response_strategy: ResponseStrategy | None = None,
    ) -> Dict[str, Any]:
        """Run the pipeline graph with the given state."""
        logger.info("[Orchestrator] Starting pipeline for session: %s", state.get("session_id"))

        try:
            validated_state = _validate_state(state)
            active_strategy = response_strategy
            if active_strategy is None:
                active_strategy = (
                    CallbackResponseStrategy(self.message_callback)
                    if self.message_callback is not None
                    else CollectingResponseStrategy()
                )

            response_token = _CURRENT_RESPONSE_STRATEGY.set(active_strategy)
            callback_token = _CURRENT_MESSAGE_CALLBACK.set(self._dispatch_event)
            try:
                await active_strategy.on_start(validated_state.session_id, validated_state.model_dump())
                final_state = await self.graph.ainvoke(validated_state.model_dump(mode="python"))

                try:
                    final_model = InternalPipelineModel.model_validate(final_state)
                    memory.save_pipeline_state(validated_state.session_id, final_model)
                    logger.info("[Orchestrator] State saved for session: %s", validated_state.session_id)
                except Exception as save_err:  # noqa: BLE001
                    logger.error("[Orchestrator] Failed to save state: %s", save_err)

                await active_strategy.on_complete(validated_state.session_id, final_state)
                return final_state
            finally:
                _CURRENT_MESSAGE_CALLBACK.reset(callback_token)
                _CURRENT_RESPONSE_STRATEGY.reset(response_token)
        except Exception as exc:  # noqa: BLE001
            logger.error("[Orchestrator] Critical failure: %s", exc, exc_info=True)
            try:
                strategy = response_strategy or (
                    CallbackResponseStrategy(self.message_callback)
                    if self.message_callback is not None
                    else CollectingResponseStrategy()
                )
                await strategy.on_error(state.get("session_id", ""), str(exc))
            except Exception:
                logger.debug("[Orchestrator] Failed to emit error response", exc_info=True)
            return {**state, "errors": [{"step": "orchestrator", "error": str(exc)}]}


__all__ = [
    "AgentState",
    "CallbackResponseStrategy",
    "CollectingResponseStrategy",
    "DSOrchestrator",
    "ResponseStrategy",
    "build_pipeline_graph",
    "create_initial_state",
    "create_pipeline",
    "data_cleaning_node",
    "data_ingest_node",
    "documentation_node",
    "eda_node",
    "execute_code_node",
    "model_selection_node",
    "optimization_node",
    "route_after_execution",
    "route_after_testing",
    "route_entry",
    "should_do_eda",
    "testing_node",
]
