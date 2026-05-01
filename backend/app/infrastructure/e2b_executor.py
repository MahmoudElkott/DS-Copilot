# backend/app/core/e2b_executor.py
import logging
import time
from typing import Optional

from app.infrastructure.executor import BaseExecutor, ExecutionResult, ExecutionStreamHandler, resolve_stream_handler

logger = logging.getLogger(__name__)


class E2BExecutor(BaseExecutor):
    """Execute Python code in E2B cloud sandbox."""

    def __init__(
        self,
        api_key: str,
        session_id: Optional[str] = None,
        stream_handler: Optional[ExecutionStreamHandler] = None,
    ):
        self.api_key = api_key
        self._sandbox = None
        self._session_id = session_id
        self._stream_handler = resolve_stream_handler(session_id, stream_handler)

    async def _emit_stream(
        self,
        stream_name: str,
        text: str,
        handler: Optional[ExecutionStreamHandler],
    ):
        if handler and text:
            await handler(stream_name, text if text.endswith("\n") else text + "\n")

    async def _get_sandbox(self):
        if self._sandbox is None:
            from e2b_code_interpreter import AsyncCodeInterpreter
            self._sandbox = await AsyncCodeInterpreter.create(
                api_key=self.api_key
            )
        return self._sandbox

    async def execute(
        self,
        code: str,
        timeout: int = 120,
        stream_handler: Optional[ExecutionStreamHandler] = None,
    ) -> ExecutionResult:
        start_time = time.time()
        active_handler = stream_handler or self._stream_handler
        try:
            sandbox = await self._get_sandbox()
            execution = await sandbox.notebook.exec_cell(
                code, timeout=timeout
            )

            stdout = "\n".join(
                [r.text for r in execution.results if hasattr(r, "text")]
            )
            stderr = "\n".join(execution.logs.stderr) if execution.logs.stderr else ""

            if execution.logs.stdout:
                for line in execution.logs.stdout:
                    await self._emit_stream("stdout", str(line), active_handler)
            if execution.logs.stderr:
                for line in execution.logs.stderr:
                    await self._emit_stream("stderr", str(line), active_handler)

            if stdout:
                for line in stdout.splitlines():
                    await self._emit_stream("stdout", line, active_handler)

            if execution.error:
                error_text = (
                    f"{execution.error.name}: {execution.error.value}\n"
                    f"{execution.error.traceback}"
                )
                await self._emit_stream("stderr", error_text, active_handler)
                return ExecutionResult(
                    success=False,
                    stdout=stdout,
                    stderr=error_text,
                    exit_code=1,
                    execution_time=time.time() - start_time,
                )

            return ExecutionResult(
                success=True,
                stdout=stdout + "\n" + "\n".join(execution.logs.stdout),
                stderr=stderr,
                exit_code=0,
                execution_time=time.time() - start_time,
            )
        except Exception as e:
            await self._emit_stream("stderr", str(e), active_handler)
            return ExecutionResult(
                success=False,
                stdout="",
                stderr=str(e),
                exit_code=1,
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
