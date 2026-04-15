# backend/app/agents/__init__.py
"""
DS-Copilot Multi-Agent System.

Each agent is a specialized worker that handles one step
in the data science pipeline. All agents follow the same pattern:

1. Get LLM model via llm_router.get_model(task_type=...)
2. Build prompt with dataset context from shared state
3. Execute generated code via harness with self-healing
4. Return state update dict with messages, generated_code, steps_completed
"""

from app.agents.data_ingest_agent import DataIngestAgent
from app.agents.data_cleaning_agent import DataCleaningAgent
from app.agents.eda_agent import EDAAgent
from app.agents.model_selection_agent import ModelSelectionAgent
from app.agents.code_writer_agent import CodeWriterAgent
from app.agents.testing_agent import TestingAgent
from app.agents.optimization_agent import OptimizationAgent
from app.agents.documentation_agent import DocumentationAgent

__all__ = [
    "DataIngestAgent",
    "DataCleaningAgent",
    "EDAAgent",
    "ModelSelectionAgent",
    "CodeWriterAgent",
    "TestingAgent",
    "OptimizationAgent",
    "DocumentationAgent",
]
