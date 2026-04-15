# backend/app/core/local_executor.py
import subprocess
import os
import time
import sys
import asyncio
import logging

from app.core.executor import BaseExecutor, ExecutionResult

logger = logging.getLogger(__name__)


class LocalExecutor(BaseExecutor):
    """Execute Python code in a local sandboxed environment."""

    def __init__(self, sandbox_dir: str = "./sandbox"):
        self.sandbox_dir = os.path.abspath(sandbox_dir)
        os.makedirs(self.sandbox_dir, exist_ok=True)
        self.venv_path = os.path.join(self.sandbox_dir, ".venv")
        self._venv_ready = False

    def _ensure_venv(self):
        """Lazy venv creation — only called when code execution is needed."""
        if self._venv_ready:
            return
        if os.path.exists(self._get_python_path()):
            self._venv_ready = True
            return
        try:
            logger.info(f"[Executor] Creating sandbox venv at {self.venv_path}...")
            subprocess.run(
                [sys.executable, "-m", "venv", self.venv_path],
                check=True,
                capture_output=True,
            )
            # Install base packages
            pip = self._get_pip_path()
            logger.info("[Executor] Installing base packages in sandbox venv...")
            subprocess.run(
                [pip, "install", "pandas", "numpy", "scikit-learn",
                 "matplotlib", "seaborn", "xgboost", "lightgbm",
                 "plotly", "openpyxl", "sqlalchemy"],
                check=True,
                capture_output=True,
            )
            self._venv_ready = True
            logger.info("[Executor] Sandbox venv ready!")
        except Exception as e:
            logger.error(f"[Executor] Failed to create sandbox venv: {e}")
            raise RuntimeError(
                f"Failed to create sandbox venv. "
                f"Try manually: python -m venv {self.venv_path}"
            ) from e

    def _get_python_path(self):
        if os.name == "nt":
            return os.path.join(self.venv_path, "Scripts", "python.exe")
        return os.path.join(self.venv_path, "bin", "python")

    def _get_pip_path(self):
        if os.name == "nt":
            return os.path.join(self.venv_path, "Scripts", "pip.exe")
        return os.path.join(self.venv_path, "bin", "pip")

    async def execute(self, code: str, timeout: int = 120) -> ExecutionResult:
        self._ensure_venv()  # Lazy venv creation
        start_time = time.time()

        # Write code to temp file inside sandbox
        code_file = os.path.join(self.sandbox_dir, "_current_run.py")
        with open(code_file, "w", encoding="utf-8") as f:
            f.write(code)

        try:
            process = await asyncio.create_subprocess_exec(
                self._get_python_path(),
                code_file,
                cwd=self.sandbox_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=timeout
            )

            execution_time = time.time() - start_time

            # Detect created files
            files_created = self._detect_new_files()

            return ExecutionResult(
                success=process.returncode == 0,
                stdout=stdout.decode("utf-8", errors="replace"),
                stderr=stderr.decode("utf-8", errors="replace"),
                execution_time=execution_time,
                files_created=files_created,
            )
        except asyncio.TimeoutError:
            return ExecutionResult(
                success=False,
                stdout="",
                stderr=f"Execution timed out after {timeout}s",
                execution_time=timeout,
            )
        except Exception as e:
            return ExecutionResult(
                success=False,
                stdout="",
                stderr=str(e),
                execution_time=time.time() - start_time,
            )

    async def install_package(self, package: str) -> bool:
        try:
            process = await asyncio.create_subprocess_exec(
                self._get_pip_path(), "install", package,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await process.communicate()
            return process.returncode == 0
        except Exception:
            return False

    async def upload_file(self, filename: str, content: bytes) -> str:
        filepath = os.path.join(self.sandbox_dir, filename)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "wb") as f:
            f.write(content)
        return filepath

    async def download_file(self, filepath: str) -> bytes:
        full_path = os.path.join(self.sandbox_dir, filepath)
        with open(full_path, "rb") as f:
            return f.read()

    def _detect_new_files(self) -> list:
        files = []
        for root, dirs, filenames in os.walk(self.sandbox_dir):
            # Skip venv
            dirs[:] = [d for d in dirs if d != ".venv"]
            for fname in filenames:
                if fname.startswith("_current_run"):
                    continue
                files.append(os.path.relpath(
                    os.path.join(root, fname), self.sandbox_dir
                ))
        return files
