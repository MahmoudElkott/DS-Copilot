# backend/app/core/e2b_executor.py
import time
import logging

from app.core.executor import BaseExecutor, ExecutionResult

logger = logging.getLogger(__name__)


class E2BExecutor(BaseExecutor):
    """Execute Python code in E2B cloud sandbox."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self._sandbox = None

    async def _get_sandbox(self):
        if self._sandbox is None:
            from e2b_code_interpreter import AsyncCodeInterpreter
            self._sandbox = await AsyncCodeInterpreter.create(
                api_key=self.api_key
            )
        return self._sandbox

    async def execute(self, code: str, timeout: int = 120) -> ExecutionResult:
        start_time = time.time()
        try:
            sandbox = await self._get_sandbox()
            execution = await sandbox.notebook.exec_cell(
                code, timeout=timeout
            )

            stdout = "\n".join(
                [r.text for r in execution.results if hasattr(r, "text")]
            )
            stderr = "\n".join(execution.logs.stderr) if execution.logs.stderr else ""

            if execution.error:
                return ExecutionResult(
                    success=False,
                    stdout=stdout,
                    stderr=f"{execution.error.name}: {execution.error.value}\n{execution.error.traceback}",
                    execution_time=time.time() - start_time,
                )

            return ExecutionResult(
                success=True,
                stdout=stdout + "\n" + "\n".join(execution.logs.stdout),
                stderr=stderr,
                execution_time=time.time() - start_time,
            )
        except Exception as e:
            return ExecutionResult(
                success=False,
                stdout="",
                stderr=str(e),
                execution_time=time.time() - start_time,
            )

    async def install_package(self, package: str) -> bool:
        result = await self.execute(f"!pip install {package}")
        return result.success

    async def upload_file(self, filename: str, content: bytes) -> str:
        sandbox = await self._get_sandbox()
        await sandbox.filesystem.write(f"/home/user/{filename}", content)
        return f"/home/user/{filename}"

    async def download_file(self, filepath: str) -> bytes:
        sandbox = await self._get_sandbox()
        return await sandbox.filesystem.read(filepath)

    async def close(self):
        if self._sandbox:
            await self._sandbox.close()
            self._sandbox = None
