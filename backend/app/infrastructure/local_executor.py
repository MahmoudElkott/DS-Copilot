import asyncio
import logging
import os
import shutil
import subprocess
import sys
import time
import hashlib
import json
from typing import Optional, Dict

from app.infrastructure.executor import BaseExecutor, ExecutionResult, ExecutionStreamHandler, resolve_stream_handler
from app.agent.tools.file_handler import FileHandler

logger = logging.getLogger(__name__)


class LocalExecutor(BaseExecutor):
    """Execute Python code in a local sandboxed environment."""

    BASE_PACKAGES = [
        "pandas",
        "numpy",
        "scikit-learn",
        "matplotlib",
        "seaborn",
        "openpyxl",
        "sqlalchemy",
    ]

    def __init__(
        self,
        sandbox_dir: str = "./sandbox",
        python_interpreter: Optional[str] = None,
        session_id: Optional[str] = None,
        stream_handler: Optional[ExecutionStreamHandler] = None,
    ):
        self.sandbox_dir = os.path.abspath(sandbox_dir)
        os.makedirs(self.sandbox_dir, exist_ok=True)
        self.venv_path = os.path.join(self.sandbox_dir, ".venv")
        if python_interpreter:
            resolved = python_interpreter
            if not os.path.exists(resolved):
                resolved = shutil.which(python_interpreter) or python_interpreter
            self.python_interpreter = os.path.abspath(resolved)
        else:
            self.python_interpreter = None
        self._venv_ready = False
        self._session_id = session_id
        self._stream_handler = resolve_stream_handler(session_id, stream_handler)

    @property
    def _uses_external_interpreter(self) -> bool:
        return bool(self.python_interpreter)

    def _ensure_venv(self):
        """Lazy venv creation — only called when code execution is needed."""
        if self._uses_external_interpreter:
            return
        if self._venv_ready:
            return
        if os.path.exists(self._get_python_path()):
            self._ensure_base_packages()
            self._venv_ready = True
            return
        try:
            logger.info(f"[Executor] Creating sandbox venv at {self.venv_path}...")
            subprocess.run(
                [sys.executable, "-m", "venv", self.venv_path],
                check=True,
                capture_output=True,
            )
            self._install_base_packages()
            self._venv_ready = True
            logger.info("[Executor] Sandbox venv ready!")
        except Exception as e:
            logger.error(f"[Executor] Failed to create sandbox venv: {e}")
            raise RuntimeError(
                f"Failed to create sandbox venv. "
                f"Try manually: python -m venv {self.venv_path}"
            ) from e

    def _install_base_packages(self):
        python = self._get_python_path()
        logger.info("[Executor] Installing base packages in sandbox venv...")
        # Some Windows venvs may not expose pip.exe; use python -m pip reliably.
        subprocess.run(
            [python, "-m", "ensurepip", "--upgrade"],
            check=False,
            capture_output=True,
        )
        subprocess.run(
            [python, "-m", "pip", "install", "--upgrade", "pip"],
            check=False,
            capture_output=True,
        )
        subprocess.run(
            [python, "-m", "pip", "install", *self.BASE_PACKAGES],
            check=True,
            capture_output=True,
        )

    def _ensure_base_packages(self):
        """Ensure core DS packages exist in an existing sandbox venv."""
        req_path = os.path.join(self.sandbox_dir, "requirements.txt")
        hash_path = os.path.join(self.sandbox_dir, ".req_hash")
        
        current_hash = ""
        if os.path.exists(req_path):
            with open(req_path, "rb") as f:
                current_hash = hashlib.md5(f.read()).hexdigest()
        
        saved_hash = ""
        if os.path.exists(hash_path):
            with open(hash_path, "r") as f:
                saved_hash = f.read().strip()
                
        check_code = (
            "import importlib.util, sys;"
            "mods=['pandas','numpy','sklearn','matplotlib','seaborn','openpyxl','sqlalchemy'];"
            "missing=[m for m in mods if importlib.util.find_spec(m) is None];"
            "print(','.join(missing));"
            "sys.exit(1 if missing else 0)"
        )

        check = subprocess.run(
            [self._get_python_path(), "-c", check_code],
            capture_output=True,
            text=True,
        )
        
        needs_install = False
        missing = "pandas"
        if check.returncode != 0:
            needs_install = True
            missing = check.stdout.strip() or "pandas"
        elif current_hash and current_hash != saved_hash:
            needs_install = True
            missing = "requirements.txt changed"
            
        if needs_install:
            logger.info(f"[Executor] Missing packages or deps changed: {missing}; reinstalling")
            self._install_base_packages()
            if os.path.exists(req_path):
                subprocess.run(
                    [self._get_python_path(), "-m", "pip", "install", "-r", req_path],
                    check=False, capture_output=True
                )
            if current_hash:
                with open(hash_path, "w") as f:
                    f.write(current_hash)

    def _get_python_path(self):
        if self._uses_external_interpreter:
            return self.python_interpreter
        if os.name == "nt":
            return os.path.join(self.venv_path, "Scripts", "python.exe")
        return os.path.join(self.venv_path, "bin", "python")

    def _get_pip_path(self):
        if self._uses_external_interpreter:
            return ""
        if os.name == "nt":
            return os.path.join(self.venv_path, "Scripts", "pip.exe")
        return os.path.join(self.venv_path, "bin", "pip")

    async def _stream_pipe(
        self,
        stream: asyncio.StreamReader,
        stream_name: str,
        chunks: list[str],
        handler: Optional[ExecutionStreamHandler],
    ) -> None:
        while True:
            line = await stream.readline()
            if not line:
                break
            text = line.decode("utf-8", errors="replace")
            chunks.append(text)
            if handler:
                await handler(stream_name, text)

    async def execute(
        self,
        code: str,
        timeout: int = 120,
        stream_handler: Optional[ExecutionStreamHandler] = None,
        context_config: Optional[Dict[str, str]] = None,
    ) -> ExecutionResult:
        # Command Sanitization
        from app.infrastructure.sanitizer import CommandSanitizer
        allowed_paths = FileHandler.get_allowed_paths(context_config=context_config, sandbox_dir=self.sandbox_dir)
        is_safe, violations = CommandSanitizer.sanitize(code, allowed_paths=allowed_paths)
        if not is_safe:
            violation_msg = f"Security Violation: Restricted operations detected: {', '.join(violations)}"
            logger.warning(f"[Executor] {violation_msg}")
            return ExecutionResult(
                success=False,
                stdout="",
                stderr=violation_msg,
                exit_code=1,
                execution_time=0.0,
            )

        self._ensure_venv()  # Lazy venv creation
        start_time = time.time()
        active_handler = stream_handler or self._stream_handler

        python_path = self._get_python_path()
        if not python_path or not os.path.exists(python_path):
            return ExecutionResult(
                success=False,
                stdout="",
                stderr=f"Python interpreter not found: {python_path}",
                exit_code=1,
                execution_time=0.0,
            )

        # Write code to temp file inside sandbox
        code_file = os.path.join(self.sandbox_dir, "_current_run.py")
        with open(code_file, "w", encoding="utf-8") as f:
            f.write(code)

        env = os.environ.copy()
        if context_config:
            config_file = os.path.join(self.sandbox_dir, "context_config.json")
            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(context_config, f)
            env.update(context_config)

        process = None
        try:
            process = await asyncio.create_subprocess_exec(
                python_path,
                code_file,
                cwd=self.sandbox_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
            )

            stdout_chunks: list[str] = []
            stderr_chunks: list[str] = []

            stdout_task = asyncio.create_task(
                self._stream_pipe(
                    process.stdout,
                    "stdout",
                    stdout_chunks,
                    active_handler,
                )
            )
            stderr_task = asyncio.create_task(
                self._stream_pipe(
                    process.stderr,
                    "stderr",
                    stderr_chunks,
                    active_handler,
                )
            )

            await asyncio.wait_for(process.wait(), timeout=timeout)
            await asyncio.gather(stdout_task, stderr_task, return_exceptions=True)

            execution_time = time.time() - start_time
            stdout = "".join(stdout_chunks)
            stderr = "".join(stderr_chunks)

            # Detect created files
            files_created = self._detect_new_files()

            return ExecutionResult(
                success=process.returncode == 0,
                stdout=stdout,
                stderr=stderr,
                exit_code=process.returncode,
                execution_time=execution_time,
                files_created=files_created,
            )
        except asyncio.TimeoutError:
            timeout_msg = f"Execution timed out after {timeout}s"
            try:
                if process is not None:
                    process.kill()
                    await process.wait()
            except Exception:  # noqa: BLE001
                logger.debug("Process kill failed after timeout", exc_info=True)
            if active_handler:
                await active_handler("stderr", timeout_msg + "\n")
            return ExecutionResult(
                success=False,
                stdout="",
                stderr=timeout_msg,
                exit_code=-1,
                execution_time=timeout,
            )
        except Exception as e:
            return ExecutionResult(
                success=False,
                stdout="",
                stderr=str(e),
                exit_code=1,
                execution_time=time.time() - start_time,
            )

    async def install_package(self, package: str) -> bool:
        if not self._uses_external_interpreter:
            self._ensure_venv()
        try:
            process = await asyncio.create_subprocess_exec(
                self._get_python_path(), "-m", "pip", "install", package,
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
