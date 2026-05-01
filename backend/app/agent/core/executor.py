import logging
import asyncio
from typing import Dict, Any, Type, Callable, Awaitable
from langchain_core.messages import AIMessage
from app.infrastructure.memory import memory
from app.models.schemas import InternalPipelineModel

# Agents (Importing from existing paths for now, will modularize later)
from app.agents.data_ingest_agent import DataIngestAgent
from app.agents.data_cleaning_agent import DataCleaningAgent
from app.agents.eda_agent import EDAAgent
from app.agents.model_selection_agent import ModelSelectionAgent
from app.agents.code_writer_agent import CodeWriterAgent
from app.agents.testing_agent import TestingAgent
from app.agents.optimization_agent import OptimizationAgent
from app.agents.documentation_agent import DocumentationAgent

logger = logging.getLogger(__name__)

class AgentExecutor:
    """Delegates task execution to specific agents with retry and timeout logic."""

    def __init__(
        self, 
        max_retries: int = 3, 
        timeout: int = 120, 
        message_callback: Callable[[Dict[str, Any]], Awaitable[None]] | None = None
    ):
        self.max_retries = max_retries
        self.timeout = timeout
        self.message_callback = message_callback

    async def _run_node(self, agent_cls: Type, state: Dict[str, Any], step_key: str) -> Dict[str, Any]:
        from app.infrastructure.llm_router import llm_router
        from app.config import LLMProvider, settings
        
        user_settings = state.get("user_settings", {})
        provider = user_settings.get("llm_provider")
        
        # Circuit Breaker Logic
        if provider == "local" or provider == LLMProvider.LOCAL:
            if not llm_router._local_health_status:
                logger.warning(f"[Executor] Local model unreachable for {step_key}. Failing over to {settings.FALLBACK_LLM_PROVIDER.value}")
                # Inject failover warning into messages
                warn_msg = "⚠️ Local model unreachable, failing over to cloud provider."
                state.setdefault("messages", []).append(AIMessage(content=warn_msg))
                if self.message_callback:
                    await self.message_callback({
                        "type": "log",
                        "agent": "executor",
                        "content": warn_msg,
                        "metadata": {"step": step_key, "level": "warning"}
                    })

        if self.message_callback:
            await self.message_callback({
                "type": "agent_action",
                "agent": step_key,
                "content": f"Agent {step_key} is now processing...",
                "metadata": {"step": step_key, "action": "start"}
            })

        for attempt in range(self.max_retries):
            try:
                # Actual agent execution
                # Note: The agents themselves will call the executor via tools.
                # However, for the general execution node (Task 6 requirement), 
                # we need to ensure the sanitizer is used.
                result = await asyncio.wait_for(agent_cls.run(state), timeout=self.timeout)
                
                # Save to memory
                msg_content = result["messages"][0].content if result.get("messages") else f"{step_key} completed"
                memory.save_message(
                    session_id=state["session_id"],
                    role="agent",
                    content=msg_content,
                    agent_name=agent_cls.NAME,
                )

                # Emit completion and notebook cells
                if self.message_callback:
                    await self.message_callback({
                        "type": "status",
                        "agent": step_key,
                        "content": f"{step_key} phase complete.",
                        "metadata": {"step": step_key, "action": "complete"}
                    })
                    # Use a helper to parse cells and emit
                    from app.agent.tools.notebook_utils import split_into_cells
                    cells = split_into_cells(msg_content)
                    for i, cell in enumerate(cells):
                        await self.message_callback({
                            "type": "notebook_cell",
                            "agent": "assistant",
                            "content": cell["content"],
                            "metadata": {
                                "cell_type": cell["type"],
                                "stage": step_key,
                                "cell_index": i,
                                "language": "python" if cell["type"] == "code" else "markdown",
                            },
                        })

                return result
            except asyncio.TimeoutError:
                logger.error(f"[Executor] {step_key} timeout (attempt {attempt+1}/{self.max_retries})")
                if attempt == self.max_retries - 1:
                    return self._error_state(state, step_key, "Timeout")
            except Exception as e:
                logger.error(f"[Executor] {step_key} failed: {e} (attempt {attempt+1}/{self.max_retries})")
                if attempt == self.max_retries - 1:
                    return self._error_state(state, step_key, str(e))
        return state

    def _error_state(self, state: Dict[str, Any], step: str, error: str) -> Dict[str, Any]:
        errors = list(state.get("errors", []))
        errors.append({"step": step, "error": error})
        return {
            "errors": errors,
            "current_step": f"{step}_error",
            "messages": [AIMessage(content=f"{step} failed: {error}")],
        }

    async def run_data_ingest(self, state: Dict[str, Any]):
        return await self._run_node(DataIngestAgent, state, "data_ingest")

    async def run_data_cleaning(self, state: Dict[str, Any]):
        return await self._run_node(DataCleaningAgent, state, "data_cleaning")

    async def run_eda(self, state: Dict[str, Any]):
        return await self._run_node(EDAAgent, state, "eda")

    async def run_model_selection(self, state: Dict[str, Any]):
        return await self._run_node(ModelSelectionAgent, state, "model_selection")

    async def run_code_writer(self, state: Dict[str, Any]):
        return await self._run_node(CodeWriterAgent, state, "code_writing")

    async def run_testing(self, state: Dict[str, Any]):
        return await self._run_node(TestingAgent, state, "testing")

    async def run_optimization(self, state: Dict[str, Any]):
        return await self._run_node(OptimizationAgent, state, "optimization")

    async def run_documentation(self, state: Dict[str, Any]):
        return await self._run_node(DocumentationAgent, state, "documentation")

    async def run_execution(self, state: Dict[str, Any]):
        # This will be refactored into its own Tool or specialized node later
        # For now, we can keep the logic from orchestrator.py or call a shared utility
        from app.agent.core.orchestrator import execute_code_node
        return await execute_code_node(state)
