# backend/app/core/harness.py
import logging
import traceback
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
import time
import json

from app.core.executor import BaseExecutor, ExecutionResult

logger = logging.getLogger(__name__)


@dataclass
class HarnessReport:
    step_name: str
    status: str = "pending"
    tests_passed: int = 0
    tests_failed: int = 0
    test_results: list = field(default_factory=list)
    execution_time: float = 0.0
    performance_metrics: dict = field(default_factory=dict)
    errors: list = field(default_factory=list)
    self_healing_attempts: int = 0
    timestamp: str = field(
        default_factory=lambda: datetime.utcnow().isoformat()
    )


class HarnessEngine:
    """
    Harness Engineering Engine:
    - Test-Driven Development (writes tests before code)
    - Error Recovery & Self-Healing
    - Performance Benchmarking
    - CI/CD Pipeline Generation
    """

    def __init__(self, executor: BaseExecutor, llm_router=None):
        self.executor = executor
        self.llm_router = llm_router
        self.reports: list = []

    # ── TDD: Generate Tests First ──────────────────────────────

    async def generate_tests(
        self, task_description: str, expected_behavior: str
    ) -> str:
        """Generate test code BEFORE the actual implementation."""
        test_prompt = f"""
You are a senior QA engineer. Write Python unit tests for the following task.
Use pytest style. Be thorough.

TASK: {task_description}
EXPECTED BEHAVIOR: {expected_behavior}

Write ONLY the test code. Include:
1. Test for correct output type
2. Test for edge cases (empty data, nulls, etc.)
3. Test for expected transformations
4. Test for error handling

```python
import pytest
import pandas as pd
import numpy as np
# ... tests here
```
"""
        if self.llm_router:
            model = self.llm_router.get_model(task_type="testing")
            from langchain_core.messages import HumanMessage
            response = await model.ainvoke([HumanMessage(content=test_prompt)])
            return self._extract_code(response.content)
        return ""

    # ── Execute with Self-Healing ──────────────────────────────

    async def execute_with_healing(
        self,
        code: str,
        step_name: str,
        max_retries: int = 3,
        fix_callback: Optional[Callable] = None,
    ) -> tuple:
        """
        Execute code with automatic error recovery.
        If it fails, attempt to self-heal by fixing the code.
        """
        report = HarnessReport(step_name=step_name)
        current_code = code
        start = time.time()

        for attempt in range(max_retries + 1):
            result = await self.executor.execute(current_code)

            if result.success:
                report.status = "passed"
                report.execution_time = time.time() - start
                self.reports.append(report)
                return result, report

            # Self-healing attempt
            report.self_healing_attempts += 1
            report.errors.append({
                "attempt": attempt + 1,
                "error": result.stderr[:1000],
            })

            logger.warning(
                f"[Harness] {step_name} failed (attempt {attempt + 1}): "
                f"{result.stderr[:200]}"
            )

            if attempt < max_retries:
                if fix_callback:
                    current_code = await fix_callback(
                        current_code, result.stderr
                    )
                elif self.llm_router:
                    current_code = await self._auto_fix(
                        current_code, result.stderr, step_name
                    )

        report.status = "failed"
        report.execution_time = time.time() - start
        self.reports.append(report)
        return result, report

    async def _auto_fix(
        self, code: str, error: str, step_name: str
    ) -> str:
        """Use LLM to automatically fix broken code."""
        fix_prompt = f"""
The following Python code for step '{step_name}' produced an error.
Fix the code and return ONLY the corrected Python code.

ORIGINAL CODE:
```python
{code}
```

ERROR:
```
{error}
```

RULES:
- Fix ONLY the error, don't change the logic
- Make sure all imports are included
- Return complete runnable code
- Add error handling where needed
"""
        model = self.llm_router.get_model(task_type="code_writing")
        from langchain_core.messages import HumanMessage
        response = await model.ainvoke([HumanMessage(content=fix_prompt)])
        return self._extract_code(response.content)

    # ── Performance Benchmarking ───────────────────────────────

    async def benchmark(
        self, code: str, iterations: int = 3
    ) -> Dict[str, Any]:
        """Benchmark code execution performance."""
        times = []
        for _ in range(iterations):
            result = await self.executor.execute(code)
            times.append(result.execution_time)

        return {
            "avg_time": sum(times) / len(times),
            "min_time": min(times),
            "max_time": max(times),
            "all_succeeded": all(True for _ in times),
        }

    # ── CI/CD Pipeline Generation ──────────────────────────────

    def generate_cicd_pipeline(self, project_name: str) -> str:
        """Generate GitHub Actions CI/CD pipeline."""
        return f"""
name: {project_name} CI/CD

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov
      - name: Run tests
        run: pytest tests/ -v --cov=src --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v3

  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Lint
        run: |
          pip install ruff
          ruff check .

  train:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v4
      - name: Train Model
        run: python src/train.py
      - name: Upload Model Artifact
        uses: actions/upload-artifact@v4
        with:
          name: model
          path: output/model.*
"""

    # ── Run Tests ──────────────────────────────────────────────

    async def run_tests(
        self, test_code: str, implementation_code: str
    ) -> HarnessReport:
        """Run generated tests against implementation."""
        combined = (
            implementation_code
            + "\n\n"
            + test_code
            + "\n\npytest.main([__file__, '-v'])"
        )

        result = await self.executor.execute(combined)

        report = HarnessReport(step_name="test_run")
        if result.success:
            report.status = "passed"
            # Parse test output
            for line in result.stdout.split("\n"):
                if "PASSED" in line:
                    report.tests_passed += 1
                elif "FAILED" in line:
                    report.tests_failed += 1
        else:
            report.status = "failed"
            report.errors.append(result.stderr)

        self.reports.append(report)
        return report

    # ── Utilities ──────────────────────────────────────────────

    def _extract_code(self, text: str) -> str:
        """Extract Python code from markdown code blocks."""
        if "```python" in text:
            parts = text.split("```python")
            if len(parts) > 1:
                code = parts[1].split("```")[0]
                return code.strip()
        if "```" in text:
            parts = text.split("```")
            if len(parts) > 1:
                return parts[1].strip()
        return text.strip()

    def get_full_report(self) -> list:
        return [
            {
                "step": r.step_name,
                "status": r.status,
                "tests_passed": r.tests_passed,
                "tests_failed": r.tests_failed,
                "execution_time": r.execution_time,
                "healing_attempts": r.self_healing_attempts,
                "errors": r.errors,
            }
            for r in self.reports
        ]
