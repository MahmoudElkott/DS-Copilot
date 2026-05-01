# FILE STRUCTURE

Current repository layout, with the main runtime and refactor surfaces called out.

```text
DS-Copilot/
├── README.md
├── FILE_STRUCTURE.md
├── docker-compose.yml
├── storage/                     # Root-level generated artifacts and project outputs (gitignored)
├── backend/
│   ├── app/
│   │   ├── agent/
│   │   │   ├── core/
│   │   │   │   ├── executor.py
│   │   │   │   ├── orchestrator.py
│   │   │   │   └── validators/
│   │   │   │       └── path_validator.py
│   │   │   └── tools/
│   │   │       └── file_handler.py
│   │   ├── agents/
│   │   │   ├── orchestrator.py      # Compatibility wrapper for the unified core orchestrator
│   │   │   ├── code_writer_agent.py
│   │   │   ├── data_cleaning_agent.py
│   │   │   ├── data_ingest_agent.py
│   │   │   ├── documentation_agent.py
│   │   │   ├── eda_agent.py
│   │   │   ├── model_selection_agent.py
│   │   │   ├── optimization_agent.py
│   │   │   └── testing_agent.py
│   │   ├── api/
│   │   │   ├── routers/
│   │   │   │   ├── files.py
│   │   │   │   └── pipeline.py
│   │   │   ├── state.py
│   │   │   └── websocket.py
│   │   ├── infrastructure/
│   │   │   ├── executor.py
│   │   │   ├── file_manager.py
│   │   │   ├── paths.py
│   │   │   ├── sanitizer.py
│   │   │   ├── local_executor.py
│   │   │   ├── docker_executor.py
│   │   │   ├── e2b_executor.py
│   │   │   ├── harness.py
│   │   │   ├── llm_router.py
│   │   │   └── startup.py
│   │   ├── middleware/
│   │   ├── models/
│   │   │   └── schemas.py
│   │   └── utils/
│   ├── sandbox/                  # Local execution sandbox (gitignored)
│   ├── tests/
│   │   ├── test_agents.py
│   │   ├── test_jupyter_system.py
│   │   └── test_path_validator.py
│   ├── test_graph.py
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── store/
│   │   │   └── appStore.js
│   │   ├── hooks/
│   │   │   └── useWebSocket.js
│   │   ├── components/
│   │   ├── context/
│   │   ├── modules/
│   │   └── utils/
│   └── package.json
└── data/
    ├── iris.csv
    └── processed/
```

Notes:

* The authoritative pipeline engine lives in `backend/app/agent/core/orchestrator.py`.
* The legacy `backend/app/agents/orchestrator.py` module is now a compatibility wrapper.
* Generated artifact roots are ignored through `.gitignore` and resolved through the shared `OUTPUT_PATH` / `OUTPUT_DIR` config.
