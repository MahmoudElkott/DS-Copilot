from typing import Dict, Any, List, Callable, Awaitable
from langgraph.graph import StateGraph, END
from app.models.schemas import InternalPipelineModel
from app.agent.core.executor import AgentExecutor

class DSPlanner:
    """Handles pipeline construction and routing logic."""
    
    def __init__(self, message_callback: Callable[[Dict[str, Any]], Awaitable[None]] | None = None):
        self.message_callback = message_callback

    @staticmethod
    def should_do_eda(state: Dict[str, Any]) -> str:
        cleaning_result = state.get("cleaning_result", {})
        current_file_path = cleaning_result.get("file_path") or state.get("dataset_path")
        if current_file_path:
            return "eda"
        return "model_selection"

    @staticmethod
    def route_after_execution(state: Dict[str, Any]) -> str:
        execution_result = state.get("execution_result", {}) or {}
        if execution_result.get("success"):
            return "testing"

        retry_count = int(state.get("retry_count", 0))
        max_retries = int(state.get("max_retries", 3))
        if retry_count < max_retries:
            return "code_writer"

        return "documentation"

    @staticmethod
    def route_after_testing(state: Dict[str, Any]) -> str:
        testing_result = state.get("testing_result", {})
        if testing_result.get("tests_failed", 0) > testing_result.get("tests_passed", 0):
            return "documentation"
        return "optimization"

    @staticmethod
    def get_entry_point(state: Dict[str, Any]) -> str:
        """Determines where the pipeline should start/resume."""
        from app.agent.tools.file_handler import FileHandler
        dataset_path = FileHandler.get_dataset_path(state)
        steps = state.get("steps_completed", [])
        
        # Check if we have a valid cleaned file to resume from
        cleaning_result = state.get("cleaning_result", {})
        if cleaning_result and cleaning_result.get("file_path"):
            if "eda" not in steps:
                return "eda"
            if "model_selection" not in steps:
                return "model_selection"
            return "code_writer"

        # If we have a dataset and both ingestion/cleaning are done, go to EDA
        if "data_ingest" in steps and "data_cleaning" in steps:
            return "eda"
        
        # Auto-resume logic: if dataset_path looks like a cleaned file
        if dataset_path and ("cleaned" in dataset_path.lower() or "processed" in dataset_path.lower()):
            return "eda"
        
        return "data_ingest"

    def build_graph(self) -> StateGraph:
        graph = StateGraph(InternalPipelineModel)
        
        executor = AgentExecutor(message_callback=self.message_callback)
        
        graph.add_node("data_ingest", executor.run_data_ingest)
        graph.add_node("data_cleaning", executor.run_data_cleaning)
        graph.add_node("eda", executor.run_eda)
        graph.add_node("model_selection", executor.run_model_selection)
        graph.add_node("code_writer", executor.run_code_writer)
        graph.add_node("execute_code", executor.run_execution)
        graph.add_node("testing", executor.run_testing)
        graph.add_node("optimization", executor.run_optimization)
        graph.add_node("documentation", executor.run_documentation)

        # Dynamic Entry Point
        graph.add_node("start_node", lambda x: x)
        graph.set_entry_point("start_node")
        graph.add_conditional_edges(
            "start_node",
            self.get_entry_point,
            {
                "eda": "eda",
                "data_ingest": "data_ingest"
            }
        )

        graph.add_edge("data_ingest", "data_cleaning")
        graph.add_conditional_edges(
            "data_cleaning",
            self.should_do_eda,
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
            self.route_after_execution,
            {
                "testing": "testing",
                "code_writer": "code_writer",
                "documentation": "documentation",
            },
        )
        graph.add_conditional_edges(
            "testing",
            self.route_after_testing,
            {
                "optimization": "optimization",
                "documentation": "documentation",
            },
        )
        graph.add_edge("optimization", "documentation")
        graph.add_edge("documentation", END)

        return graph
