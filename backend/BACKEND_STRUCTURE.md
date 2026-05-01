# Backend File Structure

This document describes the organization and purpose of the DS-Copilot backend codebase.

## Directory Tree

```
backend/
├── app/                          # Main application code
│   ├── __init__.py
│   ├── main.py                   # FastAPI app entry point
│   ├── config.py                 # Pydantic-settings configuration
│   │
│   ├── agent/                    # LangGraph orchestration & core pipeline
│   │   ├── core/                 # Pipeline engine (authoritative)
│   │   │   ├── orchestrator.py   # LangGraph StateGraph builder
│   │   │   ├── executor.py       # Code execution abstraction
│   │   │   ├── planner.py        # Step planning logic
│   │   │   └── validators/       # Input validation
│   │   │       ├── path_validator.py  # AST-based path sanitization
│   │   │       └── __init__.py
│   │   │
│   │   ├── interfaces/           # Abstract base classes
│   │   │   ├── base.py           # Agent interface contracts
│   │   │   └── __init__.py
│   │   │
│   │   └── tools/                # Shared utilities for agents
│   │       ├── file_handler.py   # File I/O operations
│   │       ├── notebook_utils.py # Jupyter notebook handling
│   │       └── __init__.py
│   │
│   ├── agents/                   # Individual pipeline stage agents
│   │   ├── orchestrator.py       # Compatibility wrapper (re-exports agent/core/orchestrator)
│   │   ├── data_ingest_agent.py  # Dataset loading & parsing
│   │   ├── data_cleaning_agent.py # Data preprocessing & imputation
│   │   ├── eda_agent.py          # Exploratory data analysis
│   │   ├── model_selection_agent.py # Model recommendation engine
│   │   ├── code_writer_agent.py  # Code generation
│   │   ├── testing_agent.py      # Test suite generation
│   │   ├── optimization_agent.py # Hyperparameter tuning
│   │   ├── documentation_agent.py # Report generation
│   │   ├── __init__.py
│   │
│   ├── api/                      # REST & WebSocket endpoints
│   │   ├── routes.py             # Main route dispatcher
│   │   ├── websocket.py          # WebSocket connection manager
│   │   ├── state.py              # Response state tracking
│   │   ├── routers/              # Modular endpoint groups
│   │   │   ├── chat.py           # Chat message endpoints
│   │   │   ├── files.py          # File upload/download
│   │   │   ├── notebook.py       # Notebook cell execution
│   │   │   ├── pipeline.py       # Pipeline control (START, STOP, etc)
│   │   │   ├── sessions.py       # Session management
│   │   │   ├── settings.py       # Settings endpoints
│   │   │   └── __init__.py
│   │   └── __init__.py
│   │
│   ├── infrastructure/           # Core services & utilities
│   │   ├── executor.py           # BaseExecutor interface
│   │   ├── local_executor.py     # Local sandbox execution
│   │   ├── docker_executor.py    # Docker container execution
│   │   ├── e2b_executor.py       # E2B cloud sandbox integration
│   │   ├── llm_router.py         # LLM provider selection & health checks
│   │   ├── memory.py             # SQLAlchemy database layer (MemoryManager)
│   │   ├── file_manager.py       # File system operations
│   │   ├── git_manager.py        # Git integration
│   │   ├── jupyter_system.py     # Jupyter kernel wrapper
│   │   ├── sanitizer.py          # CommandSanitizer (regex-based safety)
│   │   ├── paths.py              # Path management & validation
│   │   ├── settings_manager.py   # LLM settings persistence
│   │   ├── prompts.py            # System prompts for agents
│   │   ├── utils.py              # Helper functions
│   │   ├── startup.py            # Application startup hooks
│   │   ├── harness.py            # Test harness utilities
│   │   └── __init__.py
│   │
│   ├── middleware/               # ASGI middleware
│   │   ├── error_handler.py      # Global exception handling
│   │   ├── file_validator.py     # File upload validation
│   │   ├── rate_limiter.py       # Rate limiting
│   │   └── __init__.py
│   │
│   ├── models/                   # Data schemas & database models
│   │   ├── schemas.py            # Pydantic models
│   │   │                         #   - InternalPipelineModel (LangGraph state)
│   │   │                         #   - AgentStateModel (REST validation)
│   │   │                         #   - BaseMessage, ToolMessage, etc
│   │   ├── database.py           # SQLAlchemy ORM models
│   │   │                         #   - ConversationMessage
│   │   │                         #   - ProjectState
│   │   │                         #   - PipelineSession
│   │   └── __init__.py
│   │
│   ├── llm/                      # LLM provider implementations
│   │   ├── providers/
│   │   │   ├── openai.py         # OpenAI API client
│   │   │   └── __init__.py
│   │   └── (other providers as needed)
│   │
│   ├── utils/                    # General utilities
│   │   ├── helpers.py            # Common helper functions
│   │   ├── system.py             # System/OS utilities
│   │   └── __init__.py
│   │
│   └── __init__.py
│
├── tests/                        # Test suite
│   ├── conftest.py               # Pytest fixtures & configuration
│   ├── __init__.py
│   ├── test_api.py               # API endpoint tests
│   ├── test_agents.py            # Agent behavior tests
│   ├── test_orchestrator.py      # Pipeline orchestration tests
│   ├── test_path_validator.py    # Path validation tests
│   ├── fixtures/
│   │   └── sample_data.csv       # Test dataset
│   └── mocks/
│       ├── mock_llm.py           # Mock LLM for testing
│       └── __init__.py
│
├── sandbox/                      # Isolated execution environment (gitignored)
│   ├── .venv/                    # Virtual environment for sandboxed code
│   └── _current_run.py           # Generated agent code executes here
│
├── data/                         # Runtime data (gitignored)
│   └── db/
│       └── ds_copilot.db         # SQLite database
│
├── requirements.txt              # Python dependencies
├── Dockerfile                    # Docker image definition
└── BACKEND_STRUCTURE.md          # This file
```

## Key Components

### 1. **agent/core/** — Pipeline Orchestration
The authoritative pipeline engine. Builds LangGraph `StateGraph` with nodes for:
- Data Ingest
- Data Cleaning
- Exploratory Data Analysis
- Model Selection
- Code Writing
- Execution
- Testing
- Optimization
- Documentation

Features:
- Conditional routing for self-healing retries
- EDA skipping logic
- Test-failure routing
- Session resumability via step tracking

**Key Files:**
- `orchestrator.py` — Main pipeline builder
- `executor.py` — Code execution interface (factory pattern)
- `planner.py` — Step planning
- `validators/path_validator.py` — AST-based path safety

### 2. **agents/** — Individual Agents
Static classes with `NAME` attribute and async `run(state)` method. Each handles one pipeline stage. Most are wrappers that delegate to `agent/core/orchestrator.py`.

**Agents:**
- `data_ingest_agent.py` — Load CSV/Parquet/SQL data
- `data_cleaning_agent.py` — Handle missing values, outliers, duplicates
- `eda_agent.py` — Generate statistical summaries, visualizations
- `model_selection_agent.py` — Recommend model types & hyperparameters
- `code_writer_agent.py` — Generate training/evaluation code
- `testing_agent.py` — Create test suites
- `optimization_agent.py` — Tune hyperparameters
- `documentation_agent.py` — Generate final reports

### 3. **api/** — HTTP & WebSocket Interface

**Routes (in `routers/`):**
- `chat.py` — Message endpoints
- `files.py` — Upload/download artifacts
- `notebook.py` — Jupyter cell execution
- `pipeline.py` — Pipeline control (`START_PIPELINE`, `STOP_PIPELINE`, etc)
- `sessions.py` — Session CRUD
- `settings.py` — LLM provider configuration

**WebSocket:**
- `websocket.py` — Bidirectional real-time communication
- Server messages: `status`, `code`, `log`, `error`, `result`, `agent_action`, `notebook_cell`, `terminal`, `progress`
- Client messages: `chat`, `command` (e.g., `START_PIPELINE`)

### 4. **infrastructure/** — Core Services

| Module | Purpose |
|--------|---------|
| `executor.py` | Abstract base; factory returns `LocalExecutor`, `DockerExecutor`, or `E2BExecutor` |
| `local_executor.py` | Runs code in `backend/sandbox/` venv; streams stdout/stderr |
| `docker_executor.py` | Executes in Docker container |
| `e2b_executor.py` | Uses E2B cloud sandbox |
| `llm_router.py` | Singleton; picks provider + model per task; health checks & fallback |
| `memory.py` | SQLAlchemy + SQLite; `MemoryManager` singleton; 3 tables |
| `sanitizer.py` | `CommandSanitizer`; regex blocks dangerous ops (os.remove, subprocess, socket, HTTP) |
| `paths.py` | `GlobalPathManager`; resolves `storage/` and sandbox directories |
| `jupyter_system.py` | Jupyter kernel wrapper for notebook execution |
| `settings_manager.py` | Persists LLM settings to `backend/settings.json` |
| `prompts.py` | System prompts for agents |

### 5. **models/** — Data Schemas

**schemas.py:**
- `InternalPipelineModel` — LangGraph state (carries dataset path, results, code, retry counters)
- `AgentStateModel` — Strict Pydantic twin for REST validation
- `BaseMessage`, `ToolMessage`, etc. — LangGraph message types

**database.py:**
- `ConversationMessage` — Chat history
- `ProjectState` — Project metadata
- `PipelineSession` — Full `InternalPipelineModel` dumps for resume

### 6. **middleware/** — ASGI Middleware

| Module | Purpose |
|--------|---------|
| `error_handler.py` | Global exception handling |
| `file_validator.py` | File upload validation |
| `rate_limiter.py` | Rate limiting |

### 7. **utils/** — General Helpers

- `helpers.py` — Common functions
- `system.py` — OS utilities

## Execution Flow

```
FastAPI Request
    ↓
WebSocket/REST Route
    ↓
Response Strategy Context
    (CallbackResponseStrategy for WS, CollectingResponseStrategy for REST)
    ↓
Agent Pipeline (LangGraph StateGraph)
    ↓
Agent Nodes (Static classes)
    ↓
Code Generation
    ↓
Executor Interface
    ↓
LocalExecutor / DockerExecutor / E2BExecutor
    ↓
Sandbox Execution (_current_run.py)
    ↓
Stream Results via ResponseStrategy
    ↓
Return to Client
```

## Configuration

- **Environment Variables:** `.env` → `config.py` (Pydantic-settings)
- **LLM Settings:** `backend/settings.json` (persisted by `settings_manager.py`)
- **Database Path:** Configured in `config.py` → `backend/data/db/ds_copilot.db`
- **Sandbox Path:** `backend/sandbox/` (for local execution)
- **Output Path:** `storage/` (repo root, gitignored)

## Key Patterns

1. **Response Strategy Pattern** — Decouples delivery mechanism (WebSocket vs REST) via `contextvars`
2. **Executor Factory** — `create_executor(env_type)` returns appropriate executor
3. **LLM Router Singleton** — Health checks, fallback, circuit-breaker pattern
4. **Static Agent Classes** — No instantiation; `NAME` attribute + `async run(state)` method
5. **Resumable Pipeline** — Checks `steps_completed` to jump to next incomplete node
6. **Path Validation** — Two-layer safety: `CommandSanitizer` (regex) + `PathValidator` (AST)

## Safety & Security

- **PathValidator** (AST-based) — Ensures all file paths stay within allowed directories
- **CommandSanitizer** (regex-based) — Blocks dangerous operations before execution
- **Sandbox Isolation** — Agent code runs in `backend/sandbox/` with restricted file access
- **Middleware Validation** — File uploads validated by `file_validator.py`

## Database Schema

```sql
-- conversation_messages
id, session_id, role, content, created_at

-- project_states
id, session_id, name, description, state_data, created_at, updated_at

-- pipeline_sessions
id, session_id, full_state, created_at, updated_at
```

## Running the Backend

```bash
cd backend

# Setup
python -m venv .venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Unix

pip install -r requirements.txt

# Development
uvicorn app.main:app --reload --port 8000

# Testing
pytest tests/                          # All tests
pytest tests/test_agents.py -v         # Single file
pytest tests/test_path_validator.py -k "test_name"  # Single test

# Docker
cd ..
docker-compose up  # runs backend :8000, frontend :3000, redis :6379
```

## Notes

- **Authoritative Orchestrator:** Always use `agent/core/orchestrator.py` for new pipeline work
- **Generated Code Path:** Agent-generated code saves to `storage/` (gitignored)
- **LLM Router:** Configured in `backend/settings.json`; supports OpenAI, Anthropic, Google, Ollama, LM Studio
- **Memory Manager:** SQLite database in `backend/data/db/`; initialized by `config.py`
