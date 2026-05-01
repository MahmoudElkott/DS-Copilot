# 🤖 DS-Copilot

**Autonomous Data Science Workspace powered by Multi-Agent Orchestration.**

DS-Copilot is an advanced AI-driven workspace designed to automate the complete machine learning lifecycle. The backend now centers on a single unified LangGraph orchestrator, with a shared response strategy for both WebSocket streaming and synchronous REST execution, plus an AST-based guardrail layer that blocks unsafe generated paths before execution. Whether using local LLMs through LM Studio/Ollama or cloud providers like OpenAI, DS-Copilot provides a seamless, end-to-end environment for data scientists to scale their productivity.

---

## ✨ Features

*   🤖 **Unified Multi-Agent Orchestration**: A single LangGraph pipeline shared by REST and WebSocket entry points.
*   📊 **Intelligent Data Preparation**: Automated handling of missing values, outlier detection, and exploratory data analysis.
*   🧠 **Flexible LLM Integration**: Full support for OpenAI, Anthropic, Google Gemini, Ollama, and LM Studio.
*   📓 **Interactive Notebook Editor**: A high-performance code editor for real-time interaction with agent-generated models.
*   🧪 **Self-Healing Code Execution**: Automated testing and iterative healing to resolve execution errors without human intervention.
*   🛡️ **Safety & Guardrails**: AST-based path validation and shared execution context to prevent unsafe generated code from running.
*   🎨 **Modern UI**: Sleek, multi-themed React dashboard with real-time WebSocket updates.

---

## 🛠️ Technology Stack

### Frontend
*   **Core**: React 18, Vite
*   **Styling**: Tailwind CSS, Framer Motion (Animations)
*   **State Management**: Zustand, React Context API
*   **Icons**: Lucide React

### Backend
*   **Framework**: FastAPI (Python 3.10+)
*   **Orchestration**: LangChain, LangGraph
*   **Database**: SQLAlchemy with SQLite (Local)
*   **Communication**: WebSockets for real-time agent streaming

### Infrastructure & Tools
*   **Sandbox**: Local Venv with guarded execution and root-level generated artifact storage
*   **Version Control**: Git integration with auto-commits
*   **Deployment**: Docker & Docker Compose

---

## 🚀 Setup Instructions

### 1. Clone the Repository
```bash
git clone https://github.com/MahmoudElkott/DS-Copilot.git
cd DS-Copilot
```

### 2. Backend Configuration
Navigate to the backend directory and set up the Python environment:
```bash
cd backend
python -m venv .venv
# On Linux/macOS:
source .venv/bin/activate
# On Windows:
.venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Environment Variables
Create a `.env` file in the root directory and configure your providers:
```bash
cp .env.example .env
```
Fill in your API keys for OpenAI, Anthropic, or configure local provider URLs (Ollama/LM Studio).

### 4. Frontend Configuration
Install Node modules for the React dashboard:
```bash
cd ../frontend
npm install
```

---

## 📖 Usage

### Running the Application
Use the provided `Makefile` or start the services manually:

**Start Backend:**
```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

**Start Frontend:**
```bash
cd frontend
npm run dev
```

### Typical Workflow
1.  **Configure Models**: Open the Settings modal to select your preferred LLM provider.
2.  **Upload Data**: Ingest your CSV, JSON, or Excel datasets through the Data Preparation module.
3.  **Start Pipeline**: Launch the autonomous orchestrator to begin the ML workflow.
4.  **Monitor Progress**: Watch real-time agent logs and code execution via the WebSocket stream.
5.  **Refine & Export**: Edit generated notebooks and export the final model and documentation.

---

## 📁 File Structure

See [FILE_STRUCTURE.md](FILE_STRUCTURE.md) for the current repository tree and runtime artifact layout.

---

## ⚙️ Configuration & Advanced Settings

### Agent Performance
You can tune agent behavior in `backend/app/config.py` or via the `.env` file:
*   **`MAX_RETRIES`**: Number of times the agent attempts to heal failing code (Default: 3).
*   **`API_CALL_BUDGET`**: Limit on LLM calls per session to prevent runaway costs (Default: 100).
*   **`DEFAULT_TEMPERATURE`**: Controls model creativity (Default: 0.1 for precision).

### Sandbox Security
*   **`LOCAL_SANDBOX_DIR`**: Directory where generated code is executed locally.
*   **`E2B_API_KEY`**: Required for high-security remote code execution.

---

## 🔍 Troubleshooting

| Issue | Potential Cause | Fix |
| :--- | :--- | :--- |
| **WebSocket Disconnected** | Backend server is not running or port 8000 is blocked. | Ensure `uvicorn` is active and ports are open. |
| **Model Discovery Failed** | Local provider (LM Studio/Ollama) is not accessible. | Verify the provider URL and ensure the app is running. |
| **Pipeline Stuck** | Agent reached `API_CALL_BUDGET` or encountered unrecoverable error. | Check backend logs and increase budget in `.env` if needed. |
| **File Upload Error** | Unsupported file format or large file size. | Check `backend/app/middleware/file_validator.py` for limits. |

---

## 📜 License & Acknowledgments

This project is licensed under the **MIT License**.

Special thanks to the open-source community and the developers of **LangGraph**, **FastAPI**, and **Vite** for providing the building blocks for this autonomous workspace.

---