# backend/app/agents/orchestrator.py
"""
Multi-Agent Orchestrator using LangGraph.
This is the brain of the DS-Copilot — wires all agents into a state graph.
"""

from typing import TypedDict, Annotated, Sequence, Dict, Any, Optional
from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
import operator
import json
import logging
import uuid

from app.core.llm_router import llm_router
from app.core.executor import create_executor
from app.core.harness import HarnessEngine
from app.core.memory import memory
from app.core.file_manager import FileManager
from app.core.git_manager import GitManager
from app.config import settings

from app.agents.data_ingest_agent import DataIngestAgent
from app.agents.data_cleaning_agent import DataCleaningAgent
from app.agents.eda_agent import EDAAgent
from app.agents.model_selection_agent import ModelSelectionAgent
from app.agents.code_writer_agent import CodeWriterAgent
from app.agents.testing_agent import TestingAgent
from app.agents.optimization_agent import OptimizationAgent
from app.agents.documentation_agent import DocumentationAgent

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════
# State Definition
# ══════════════════════════════════════════════════════════════

class AgentState(TypedDict):
    """Shared state across all agents."""
    # Session
    session_id: str
    project_name: str
    project_dir: str

    # Messages
    messages: Annotated[Sequence[BaseMessage], operator.add]

    # User Config
    user_settings: Dict[str, Any]

    # Dataset Info
    dataset_path: str
    dataset_info: Dict[str, Any]

    # Pipeline Results
    cleaning_result: Dict[str, Any]
    eda_result: Dict[str, Any]
    feature_engineering_result: Dict[str, Any]
    model_selection_result: Dict[str, Any]
    training_result: Dict[str, Any]
    testing_result: Dict[str, Any]
    optimization_result: Dict[str, Any]

    # Code Store
    generated_code: Dict[str, str]  # step_name -> code

    # Pipeline Control
    current_step: str
    steps_completed: list
    errors: list
    should_do_eda: bool
    should_compare_models: bool

    # Harness
    harness_reports: list

    # Final Output
    final_report: Dict[str, Any]


# ══════════════════════════════════════════════════════════════
# Node Wrapper Functions (for LangGraph)
# ══════════════════════════════════════════════════════════════

async def data_ingest_node(state: AgentState) -> dict:
    """Node: Data Ingestion."""
    try:
        result = await DataIngestAgent.run(state)
        memory.save_message(
            session_id=state["session_id"],
            role="agent",
            content=result["messages"][0].content if result.get("messages") else "Data ingest completed",
            agent_name=DataIngestAgent.NAME,
        )
        return result
    except Exception as e:
        logger.error(f"[Orchestrator] Data ingest failed: {e}")
        return {
            "errors": state.get("errors", []) + [{"step": "data_ingest", "error": str(e)}],
            "current_step": "data_ingest_error",
            "messages": [AIMessage(content=f"❌ Data ingest failed: {e}")],
        }


async def data_cleaning_node(state: AgentState) -> dict:
    """Node: Data Cleaning."""
    try:
        result = await DataCleaningAgent.run(state)
        memory.save_message(
            session_id=state["session_id"],
            role="agent",
            content=result["messages"][0].content if result.get("messages") else "Cleaning completed",
            agent_name=DataCleaningAgent.NAME,
        )
        return result
    except Exception as e:
        logger.error(f"[Orchestrator] Data cleaning failed: {e}")
        return {
            "errors": state.get("errors", []) + [{"step": "data_cleaning", "error": str(e)}],
            "current_step": "cleaning_error",
            "messages": [AIMessage(content=f"❌ Data cleaning failed: {e}")],
        }


async def eda_node(state: AgentState) -> dict:
    """Node: Exploratory Data Analysis."""
    try:
        result = await EDAAgent.run(state)
        memory.save_message(
            session_id=state["session_id"],
            role="agent",
            content=result["messages"][0].content if result.get("messages") else "EDA completed",
            agent_name=EDAAgent.NAME,
        )
        return result
    except Exception as e:
        logger.error(f"[Orchestrator] EDA failed: {e}")
        return {
            "errors": state.get("errors", []) + [{"step": "eda", "error": str(e)}],
            "current_step": "eda_error",
            "messages": [AIMessage(content=f"❌ EDA failed: {e}")],
        }


async def model_selection_node(state: AgentState) -> dict:
    """Node: Model Selection."""
    try:
        result = await ModelSelectionAgent.run(state)
        memory.save_message(
            session_id=state["session_id"],
            role="agent",
            content=result["messages"][0].content if result.get("messages") else "Model selection completed",
            agent_name=ModelSelectionAgent.NAME,
        )
        return result
    except Exception as e:
        logger.error(f"[Orchestrator] Model selection failed: {e}")
        return {
            "errors": state.get("errors", []) + [{"step": "model_selection", "error": str(e)}],
            "current_step": "model_selection_error",
            "messages": [AIMessage(content=f"❌ Model selection failed: {e}")],
        }


async def code_writer_node(state: AgentState) -> dict:
    """Node: Code Writing."""
    try:
        result = await CodeWriterAgent.run(state)
        memory.save_message(
            session_id=state["session_id"],
            role="agent",
            content=result["messages"][0].content if result.get("messages") else "Code writing completed",
            agent_name=CodeWriterAgent.NAME,
        )
        return result
    except Exception as e:
        logger.error(f"[Orchestrator] Code writing failed: {e}")
        return {
            "errors": state.get("errors", []) + [{"step": "code_writing", "error": str(e)}],
            "current_step": "code_writing_error",
            "messages": [AIMessage(content=f"❌ Code writing failed: {e}")],
        }


async def testing_node(state: AgentState) -> dict:
    """Node: Testing."""
    try:
        result = await TestingAgent.run(state)
        memory.save_message(
            session_id=state["session_id"],
            role="agent",
            content=result["messages"][0].content if result.get("messages") else "Testing completed",
            agent_name=TestingAgent.NAME,
        )
        return result
    except Exception as e:
        logger.error(f"[Orchestrator] Testing failed: {e}")
        return {
            "errors": state.get("errors", []) + [{"step": "testing", "error": str(e)}],
            "current_step": "testing_error",
            "messages": [AIMessage(content=f"❌ Testing failed: {e}")],
        }


async def optimization_node(state: AgentState) -> dict:
    """Node: Optimization."""
    try:
        result = await OptimizationAgent.run(state)
        memory.save_message(
            session_id=state["session_id"],
            role="agent",
            content=result["messages"][0].content if result.get("messages") else "Optimization completed",
            agent_name=OptimizationAgent.NAME,
        )
        return result
    except Exception as e:
        logger.error(f"[Orchestrator] Optimization failed: {e}")
        return {
            "errors": state.get("errors", []) + [{"step": "optimization", "error": str(e)}],
            "current_step": "optimization_error",
            "messages": [AIMessage(content=f"❌ Optimization failed: {e}")],
        }


async def documentation_node(state: AgentState) -> dict:
    """Node: Documentation."""
    try:
        # Set up project directory if not already set
        if not state.get("project_dir"):
            file_manager = FileManager()
            project_dir = file_manager.create_project_structure(
                state.get("project_name", "ds-project")
            )
            state["project_dir"] = project_dir

        result = await DocumentationAgent.run(state)
        memory.save_message(
            session_id=state["session_id"],
            role="agent",
            content=result["messages"][0].content if result.get("messages") else "Documentation completed",
            agent_name=DocumentationAgent.NAME,
        )

        # Git commit if enabled
        if settings.ENABLE_GIT and settings.GIT_AUTO_COMMIT and state.get("project_dir"):
            try:
                git = GitManager(state["project_dir"])
                git.commit(f"DS-Copilot: Pipeline complete for {state.get('project_name', 'project')}")
            except Exception as git_err:
                logger.warning(f"Git commit failed: {git_err}")

        return result
    except Exception as e:
        logger.error(f"[Orchestrator] Documentation failed: {e}")
        return {
            "errors": state.get("errors", []) + [{"step": "documentation", "error": str(e)}],
            "current_step": "documentation_error",
            "messages": [AIMessage(content=f"❌ Documentation failed: {e}")],
        }


# ══════════════════════════════════════════════════════════════
# Conditional Edges
# ══════════════════════════════════════════════════════════════

def should_continue_after_ingest(state: AgentState) -> str:
    """Check if ingestion succeeded and route to cleaning."""
    if "data_ingest" in state.get("errors", [{}])[-1:][0] if state.get("errors") else "":
        return END
    return "data_cleaning"


def should_do_eda(state: AgentState) -> str:
    """Check if EDA should be performed."""
    if state.get("should_do_eda", True):
        return "eda"
    return "model_selection"


def route_after_testing(state: AgentState) -> str:
    """After testing, decide whether to optimize or jump to docs."""
    testing_result = state.get("testing_result", {})
    # If tests failed badly, skip optimization
    if testing_result.get("tests_failed", 0) > testing_result.get("tests_passed", 0):
        logger.warning("[Orchestrator] Too many test failures — skipping optimization")
        return "documentation"
    return "optimization"


# ══════════════════════════════════════════════════════════════
# Build the Graph
# ══════════════════════════════════════════════════════════════

def build_pipeline_graph() -> StateGraph:
    """Build the LangGraph state graph for the full DS pipeline."""

    graph = StateGraph(AgentState)

    # Add nodes
    graph.add_node("data_ingest", data_ingest_node)
    graph.add_node("data_cleaning", data_cleaning_node)
    graph.add_node("eda", eda_node)
    graph.add_node("model_selection", model_selection_node)
    graph.add_node("code_writer", code_writer_node)
    graph.add_node("testing", testing_node)
    graph.add_node("optimization", optimization_node)
    graph.add_node("documentation", documentation_node)

    # Set entry point
    graph.set_entry_point("data_ingest")

    # Add edges
    graph.add_edge("data_ingest", "data_cleaning")
    graph.add_conditional_edges(
        "data_cleaning",
        should_do_eda,
        {
            "eda": "eda",
            "model_selection": "model_selection",
        }
    )
    graph.add_edge("eda", "model_selection")
    graph.add_edge("model_selection", "code_writer")
    graph.add_edge("code_writer", "testing")
    graph.add_conditional_edges(
        "testing",
        route_after_testing,
        {
            "optimization": "optimization",
            "documentation": "documentation",
        }
    )
    graph.add_edge("optimization", "documentation")
    graph.add_edge("documentation", END)

    return graph


def create_pipeline():
    """Create a compiled pipeline graph."""
    graph = build_pipeline_graph()
    return graph.compile()


def create_initial_state(
    session_id: str,
    dataset_path: str,
    project_name: str = "ds-project",
    user_settings: dict = None,
) -> AgentState:
    """Create the initial state for a new pipeline run."""
    return AgentState(
        session_id=session_id,
        project_name=project_name,
        project_dir="",
        messages=[],
        user_settings=user_settings or {
            "execution_env": settings.DEFAULT_EXECUTION_ENV.value,
            "llm_provider": settings.DEFAULT_LLM_PROVIDER.value,
        },
        dataset_path=dataset_path,
        dataset_info={},
        cleaning_result={},
        eda_result={},
        feature_engineering_result={},
        model_selection_result={},
        training_result={},
        testing_result={},
        optimization_result={},
        generated_code={},
        current_step="init",
        steps_completed=[],
        errors=[],
        should_do_eda=True,
        should_compare_models=True,
        harness_reports=[],
        final_report={},
    )
