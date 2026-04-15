# 🤖 DS-Copilot

> AI-Powered Data Science Pipeline Assistant

![Python](https://img.shields.io/badge/Python-3.11+-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-latest-green)
![React](https://img.shields.io/badge/React-19-blue)
![LangGraph](https://img.shields.io/badge/LangGraph-Multi--Agent-purple)

## Overview

DS-Copilot is a full-stack multi-agent data science assistant that automates the entire ML pipeline:

**Upload a dataset → Get a complete, tested, optimized ML project with documentation.**

### Pipeline Agents

| Agent | Task | Description |
|-------|------|-------------|
| 📥 Ingest | Data Loading | Loads & profiles the dataset |
| 🧹 Clean | Data Cleaning | Handles nulls, duplicates, outliers |
| 📊 EDA | Exploratory Analysis | Generates visualizations & insights |
| 🤖 Select | Model Selection | Recommends ML models for the task |
| ✍️ Code | Code Writing | Generates complete training pipeline |
| 🧪 Test | Testing | Writes & runs pytest tests |
| ⚡ Optimize | Optimization | Hyperparameter tuning & feature analysis |
| 📝 Document | Documentation | README, PLAN, CI/CD, Dockerfile |

### Features

- **Multi-LLM Support**: OpenAI, Claude, Gemini, Ollama
- **Self-Healing Code**: Automatic error detection & fixing via Harness Engine
- **Real-time Streaming**: WebSocket updates & code streaming
- **Sandboxed Execution**: Local venv or E2B cloud sandbox
- **Auto Git**: Automatic versioning of generated projects
- **Premium UI**: Dark glassmorphism with pipeline visualization

## Quick Start

### 1. Clone & Configure

```bash
cp .env.example .env
# Edit .env and add at least one API key
```

### 2. Install Dependencies

```bash
# Backend
cd backend
pip install -r requirements.txt

# Frontend
cd ../frontend
npm install
```

### 3. Run Development Servers

```bash
# Terminal 1: Backend
cd backend
uvicorn app.main:app --reload --port 8000

# Terminal 2: Frontend
cd frontend
npm run dev
```

### 4. Open the App

Visit **http://localhost:5173** → Upload a CSV → Type "start pipeline"

## Architecture

```
Frontend (React + Vite + TailwindCSS)
    │ WebSocket + REST
    │
Backend (FastAPI + LangGraph)
    ├── LLM Router (OpenAI / Claude / Gemini / Ollama)
    ├── Code Executor (Local Sandbox / E2B Cloud)
    ├── Harness Engine (TDD + Self-Healing)
    ├── Memory (SQLite)
    └── 8 Specialized Agents (LangGraph State Graph)
```

## Docker

```bash
docker-compose up --build
# Backend: http://localhost:8000
# Frontend: http://localhost:3000
```

## Testing

```bash
cd backend
python -m pytest tests/ -v
```

## API Docs

With the backend running, visit **http://localhost:8000/docs** for Swagger UI.

## License

MIT
