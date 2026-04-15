# backend/app/agents/documentation_agent.py
"""
Documentation Agent — generates all project documentation.
Creates README, PLAN, requirements, Dockerfile, and CI/CD pipeline.
"""
import json
import logging

from langchain_core.messages import HumanMessage, AIMessage
from app.core.llm_router import llm_router
from app.core.file_manager import FileManager
from app.core.harness import HarnessEngine
from app.utils.helpers import extract_code

logger = logging.getLogger(__name__)


class DocumentationAgent:
    """Agent that generates all project documentation."""

    NAME = "documentation"

    @staticmethod
    async def run(state: dict) -> dict:
        logger.info("[Agent] 📝 Documentation starting...")

        model = llm_router.get_model(task_type="documentation")
        file_manager = FileManager()

        project_name = state.get("project_name", "ds-project")
        project_dir = state.get("project_dir", "")
        dataset_info = state.get("dataset_info", {})
        cleaning_result = state.get("cleaning_result", {})
        eda_result = state.get("eda_result", {})
        model_selection = state.get("model_selection_result", {})
        training_result = state.get("training_result", {})
        testing_result = state.get("testing_result", {})
        optimization_result = state.get("optimization_result", {})
        generated_code = state.get("generated_code", {})
        harness_reports = state.get("harness_reports", [])

        # ── 1. Generate README ─────────────────────────────────

        # Build results table for README
        results_table = ""
        if isinstance(training_result, dict) and "models" in training_result:
            for m in training_result["models"]:
                name = m.get("name", "?")
                acc = m.get("accuracy", m.get("r2_score", "-"))
                f1 = m.get("f1_score", "-")
                t = m.get("training_time", "-")
                results_table += f"| {name} | {acc} | {f1} | {t} |\n"

        project_info = {
            "name": project_name,
            "description": f"Auto-generated ML pipeline for {model_selection.get('task_type', 'classification')}",
            "dataset_source": state.get("dataset_path", "N/A"),
            "dataset_shape": str(dataset_info.get("shape", "N/A")),
            "num_features": len(dataset_info.get("columns", [])),
            "target_column": model_selection.get("target_column", "N/A"),
            "task_type": model_selection.get("task_type", "N/A"),
            "cleaning_summary": json.dumps(cleaning_result, indent=2, default=str)[:500],
            "eda_summary": json.dumps(eda_result, indent=2, default=str)[:500],
            "models_summary": ", ".join([
                m.get("name", "?")
                for m in model_selection.get("recommended_models", [])
            ]),
            "results_table": results_table or "| - | - | - | - |",
        }

        readme_content = file_manager.generate_readme(project_info)

        # ── 2. Generate PLAN.md ────────────────────────────────

        steps = []
        step_names = [
            ("data_ingest", "Data Ingestion", "DataIngestAgent"),
            ("data_cleaning", "Data Cleaning", "DataCleaningAgent"),
            ("eda", "Exploratory Data Analysis", "EDAAgent"),
            ("model_selection", "Model Selection", "ModelSelectionAgent"),
            ("code_writing", "Code Writing", "CodeWriterAgent"),
            ("testing", "Testing", "TestingAgent"),
            ("optimization", "Optimization", "OptimizationAgent"),
            ("documentation", "Documentation", "DocumentationAgent"),
        ]

        completed = state.get("steps_completed", [])
        for step_key, step_name, agent_name in step_names:
            report = next(
                (r for r in harness_reports if isinstance(r, dict) and r.get("step_name") == step_key),
                {},
            )
            steps.append({
                "name": step_name,
                "agent": agent_name,
                "status": "completed" if step_key in completed else "pending",
                "description": f"Executed by {agent_name}",
                "execution_time": report.get("execution_time", 0),
            })

        plan_content = file_manager.generate_plan(steps)

        # ── 3. Generate requirements.txt ───────────────────────

        extra_packages = []
        if model_selection.get("task_type") == "classification":
            extra_packages.append("imbalanced-learn>=0.11.0")

        requirements_content = file_manager.generate_requirements(extra_packages)

        # ── 4. Generate Dockerfile ─────────────────────────────

        dockerfile_content = file_manager.generate_dockerfile(project_name)

        # ── 5. Generate CI/CD pipeline ─────────────────────────

        harness = HarnessEngine.__new__(HarnessEngine)
        harness.executor = None
        harness.llm_router = None
        harness.reports = []
        cicd_content = harness.generate_cicd_pipeline(project_name)

        # ── 6. Write all files ─────────────────────────────────

        if not project_dir:
            project_dir = file_manager.create_project_structure(project_name)

        files_written = []

        # Write documentation files
        docs = {
            "README.md": readme_content,
            "PLAN.md": plan_content,
            "requirements.txt": requirements_content,
            "Dockerfile": dockerfile_content,
            ".github/workflows/ci.yml": cicd_content,
        }

        for filepath, content in docs.items():
            written = file_manager.write_file(project_dir, filepath, content)
            files_written.append(filepath)
            logger.info(f"[Doc] Written: {written}")

        # Write generated code to src/
        code_files = {
            "data_ingest": "src/data/ingest.py",
            "data_cleaning": "src/data/clean.py",
            "eda": "src/visualization/eda.py",
            "code_writing": "src/models/train.py",
            "testing": "tests/test_pipeline.py",
            "optimization": "src/models/optimize.py",
        }

        for step_key, dest_path in code_files.items():
            code = generated_code.get(step_key, "")
            if code:
                file_manager.write_file(project_dir, dest_path, code)
                files_written.append(dest_path)

        # ── 7. Build final report ──────────────────────────────

        final_report = {
            "project_name": project_name,
            "project_dir": project_dir,
            "task_type": model_selection.get("task_type", "N/A"),
            "target_column": model_selection.get("target_column", "N/A"),
            "models_trained": len(model_selection.get("recommended_models", [])),
            "best_model": optimization_result.get("best_params", training_result.get("best_model", "N/A")),
            "best_score": optimization_result.get("best_score", "N/A"),
            "tests_passed": testing_result.get("tests_passed", 0),
            "tests_failed": testing_result.get("tests_failed", 0),
            "files_generated": files_written,
            "total_steps": len(completed) + 1,  # +1 for documentation itself
            "harness_reports_count": len(harness_reports),
        }

        return {
            "final_report": final_report,
            "current_step": "documentation_done",
            "steps_completed": state.get("steps_completed", []) + ["documentation"],
            "generated_code": {
                **state.get("generated_code", {}),
                "documentation": f"# Documentation generated\n# Files: {files_written}",
            },
            "messages": [AIMessage(
                content=f"📝 Documentation complete! Generated {len(files_written)} files: "
                        f"{', '.join(files_written)}. "
                        f"Project ready at: {project_dir}"
            )],
        }
