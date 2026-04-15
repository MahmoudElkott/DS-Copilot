# backend/app/core/git_manager.py
import subprocess
import os
import logging

logger = logging.getLogger(__name__)


class GitManager:
    """Auto Git version control."""

    def __init__(self, repo_dir: str):
        self.repo_dir = repo_dir
        self._init_repo()

    def _init_repo(self):
        if not os.path.exists(os.path.join(self.repo_dir, ".git")):
            self._run("git", "init")
            self._write_gitignore()
            self.commit("Initial commit - DS-Copilot project")

    def _run(self, *args) -> str:
        try:
            result = subprocess.run(
                args,
                cwd=self.repo_dir,
                capture_output=True,
                text=True,
            )
            return result.stdout
        except Exception as e:
            logger.error(f"Git error: {e}")
            return ""

    def _write_gitignore(self):
        gitignore = """
__pycache__/
*.pyc
.env
.venv/
*.pkl
*.pt
*.h5
data/raw/
.DS_Store
"""
        with open(
            os.path.join(self.repo_dir, ".gitignore"), "w"
        ) as f:
            f.write(gitignore)

    def commit(self, message: str):
        self._run("git", "add", "-A")
        self._run("git", "commit", "-m", message)
        logger.info(f"[Git] Committed: {message}")

    def get_log(self, n: int = 10) -> str:
        return self._run(
            "git", "log", f"-{n}", "--oneline"
        )
