# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

DS-Copilot is an autonomous data science workspace: a FastAPI backend orchestrates a multi-agent LangGraph pipeline (ingest → clean → EDA → model selection → code writing → execution → testing → optimization → documentation), while a React frontend streams real-time progress over WebSockets.

## Commands

### Backend
```bash
cd backend
python -m venv .venv && .venv\Scripts\activate   # Windows
pip install -r requirements.txt

# Run server
uvicorn app.main:app --reload --port 8000

# Run tests
pytest tests/                          # all backend tests
pytest tests/test_agents.py -v         # single file
pytest tests/test_path_validator.py -k "test_name"  # single test
```

### Frontend
```bash
cd frontend
npm install

npm run dev      # dev server (Vite)
npm run build    # production build
npm run lint     # ESLint
```

### Docker
```bash
docker-compose up          # backend :8000, frontend :3000, redis :6379
```

## Architecture

### Two Orchestrator Layers

The authoritative pipeline engine is `backend/app/agent/core/orchestrator.py`. It builds a LangGraph `StateGraph` with nodes for each pipeline stage and conditional routing (self-healing retry loops, EDA skip, test-failure routing). `backend/app/agents/orchestrator.py` is a compatibility re-export wrapper — all new orchestration work goes in `agent/core/`.

### Shared State Model

`InternalPipelineModel` (in `models/schemas.py`) is the LangGraph state schema. It carries everything: dataset path, per-stage results, generated code, retry counters, execution results, visualization payloads. The `messages` field uses LangGraph's annotated-reducer pattern (`Annotated[Sequence[BaseMessage], operator.add]`). `AgentStateModel` is the strict Pydantic twin used for REST validation.

### Execution Adapters

`infrastructure/executor.py` defines `BaseExecutor` and a factory `create_executor(env_type)` that returns `LocalExecutor`, `DockerExecutor`, or `E2BExecutor`. The `LocalExecutor` lazily creates a sandbox venv under `backend/sandbox/`, runs agent-generated code as `_current_run.py`, and streams stdout/stderr back through registered per-session sinks.

### Safety Layer

Before any code reaches the executor, `CommandSanitizer` (regex-based) blocks dangerous operations (os.remove, subprocess, socket, outbound HTTP), then `PathValidator` (AST-based) ensures all file paths stay within allowed directories. Both live in `infrastructure/sanitizer.py` and `agent/core/validators/path_validator.py`.

### LLM Router

`infrastructure/llm_router.py` — singleton `llm_router` picks provider + model per task type, with circuit-breaker health checks for local providers (LM Studio/Ollama) and automatic fallback. Persisted settings from `backend/settings.json` are loaded at import time. Supports OpenAI, Anthropic, Google, Ollama, and LM Studio (OpenAI-compatible).

### Response Strategy Pattern

The orchestrator uses `ResponseStrategy` subclasses to decouple how pipeline events are delivered: `CallbackResponseStrategy` forwards to WebSocket callbacks, `CollectingResponseStrategy` buffers for REST. This is wired via `contextvars` so agent nodes can emit events without knowing the transport.

### WebSocket Protocol

Endpoint: `ws://localhost:8000/ws/{session_id}`. Server messages are typed (`status`, `code`, `log`, `error`, `result`, `agent_action`, `notebook_cell`, `terminal`, `progress`). Client sends `chat` or `command` (e.g., `START_PIPELINE`). The `ConnectionManager` singleton manages per-session connection lists and context.

### Frontend State

Zustand store (`frontend/src/store/appStore.js`) holds pipeline steps, messages, notebook cells, terminal logs, visualization payloads, settings, and artifacts. The `useWebSocket` hook routes all server message types into the store. Session IDs persist via `localStorage` and rehydrate pipeline state on reconnect.

### Database

SQLAlchemy + SQLite via `MemoryManager` singleton (`infrastructure/memory.py`). Three tables: `conversation_messages`, `project_states`, `pipeline_sessions` (stores full `InternalPipelineModel` dumps for resume).

## Key Paths

- Generated artifacts: `storage/` (repo root, gitignored) — resolved via `GlobalPathManager` and `OUTPUT_DIR` config
- Sandbox execution: `backend/sandbox/` (gitignored) — agent code runs here
- Database: `backend/data/db/ds_copilot.db` (created by `config.py` DATABASE_PATH property)
- Persisted LLM settings: `backend/settings.json`

## Conventions

- All file paths in generated code must use `pathlib` and stay within allowed sandbox/output directories (enforced by PathValidator)
- Backend agents are static classes with a `NAME` class attribute and async `run(state)` method — they don't instantiate
- The pipeline is resumable: `route_entry()` checks `steps_completed` and jumps to the next incomplete node
- Config via `pydantic-settings`: env vars in `.env` at repo root, loaded by `backend/app/config.py`
- Frontend uses camelCase locally, maps to snake_case for API calls in `appStore.saveSettings()`
