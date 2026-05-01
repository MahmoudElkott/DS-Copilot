# backend/app/core/jupyter_system.py
import os
import pandas as pd
import numpy as np
import time
import json
import traceback
import re
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from io import StringIO
from .prompts import SANDBOX_ARCHITECT_PROMPT
from app.utils.helpers import safe_json_parse

@dataclass
class JupyterCell:
    cell_type: str
    source: str
    outputs: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cell_type": self.cell_type,
            "source": self.source,
            "outputs": self.outputs
        }

def df_info_markdown(df: pd.DataFrame, title: str = "DataFrame Summary", emoji: str = "📊", execution_time: float = 0.0) -> str:
    """
    Converts DataFrame info/describe into a production-grade Markdown summary.
    Adheres to Specification 6.
    """
    if df is None or not isinstance(df, pd.DataFrame):
        return f"### {emoji} {title}\n\nNo valid DataFrame provided."

    records = len(df)
    cols = len(df.columns)
    nulls = df.isnull().sum().sum()
    
    # Calculate memory usage
    try:
        memory = df.memory_usage(deep=True).sum() / (1024 * 1024)
        memory_str = f"{memory:.2f} MB"
    except Exception:
        memory_str = "Unknown"

    # Create summary table following Specification 3
    table = [
        f"### {emoji} {title}",
        "",
        "| Metric | Value |",
        "| :--- | ---: |",
        f"| Status | `COMPLETED` |",
        f"| Records | {records:,} |",
        f"| Columns | {cols:,} |",
        f"| Nulls | {nulls:,} |",
        f"| Time | {execution_time:.3f}s |",
        f"| Memory | {memory_str} |",
    ]
    
    return "\n".join(table)

class PathValidator:
    """
    Enforces relative-path discipline and asserts file existence.
    Adheres to Specification 2.
    """
    @staticmethod
    def validate_path(path: str):
        if os.path.isabs(path) or (os.name == 'nt' and ':' in path and not path.startswith('.')):
            raise ValueError(f"Absolute paths are forbidden: {path}")
        
    @staticmethod
    def assert_exists(path: str):
        if not os.path.exists(path):
            raise RuntimeError(f"File not found after write operation: {path}")

class StatefulSandbox:
    """
    Persistent Python Sandbox using IPython for stateful execution.
    Adheres to Specification 1.
    """
    def __init__(self):
        self.shell = None
        self.globals = {"pd": pd, "np": np, "PathValidator": PathValidator, "df_info_markdown": df_info_markdown}
        self.locals = {}
        try:
            from IPython.core.interactiveshell import InteractiveShell
            self.shell = InteractiveShell()
            # Inject helper into shell
            self.shell.push(self.globals)
        except ImportError:
            pass

    def execute(self, code: str) -> Tuple[bool, str, str, Any]:
        """Executes code and returns (success, stdout, stderr, result_object)."""
        import sys
        from io import StringIO

        stdout_io = StringIO()
        stderr_io = StringIO()
        
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = stdout_io
        sys.stderr = stderr_io

        success = True
        result_obj = None
        try:
            if self.shell:
                execution_result = self.shell.run_cell(code)
                result_obj = execution_result.result
                if execution_result.error_before_exec or execution_result.error_in_exec:
                    success = False
                    if execution_result.error_in_exec:
                        import traceback as tb_module
                        e = execution_result.error_in_exec
                        stderr_io.write("".join(tb_module.format_exception(type(e), e, e.__traceback__)))
                    elif execution_result.error_before_exec:
                        stderr_io.write(str(execution_result.error_before_exec))
            else:
                # Basic exec fallback
                # Note: exec doesn't return a value like IPython does for the last expression easily
                exec(code, self.globals, self.locals)
        except Exception:
            success = False
            import traceback as tb_module
            stderr_io.write(tb_module.format_exc())
        finally:
            stdout = stdout_io.getvalue()
            stderr = stderr_io.getvalue()
            sys.stdout = old_stdout
            sys.stderr = old_stderr

        return success, stdout, stderr, result_obj

class JupyterEngineer:
    """
    Autonomous Data Science Engineer orchestrating the 3-phase cell architecture.
    Adheres to Specification 3, 4, and 5.
    """
    def __init__(self, sandbox: Optional[StatefulSandbox] = None):
        self.sandbox = sandbox or StatefulSandbox()
        self.history: List[Dict[str, Any]] = []
        self.system_prompt = SANDBOX_ARCHITECT_PROMPT

    async def generate_and_execute(self, model: Any, task_description: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Generates code using the Ultimate Sandbox Architect Prompt and executes it.
        """
        from langchain_core.messages import HumanMessage, SystemMessage
        
        prompt_context = f"\nCONTEXT:\n{json.dumps(context, indent=2)}" if context else ""
        user_message = f"TASK: {task_description}{prompt_context}"
        
        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=user_message)
        ]
        
        response = await model.ainvoke(messages)
        cell_data = safe_json_parse(response.content)
        
        if not cell_data or "source" not in cell_data:
            # Fallback if parsing fails
            return self._handle_recovery(task_description, response.content, "Failed to parse LLM response as JSON.")

        # Execute the generated source
        success, stdout, stderr, result_obj = self.sandbox.execute(cell_data["source"])
        
        if not success:
            return self._handle_recovery(task_description, cell_data["source"], stderr)

        # Capture the result object if it's a dict (Agent summary)
        if isinstance(result_obj, dict):
            cell_data["execution_result_object"] = result_obj
            
            # Check for export_files in the dictionary summary
            if "export_files" in result_obj:
                cell_data["export_files"] = result_obj["export_files"]

        # Update outputs with actual stdout/stderr if needed, or keep the LLM's predicted markdown
        # Handle [EXPORT_READY] tag in stdout
        if "[EXPORT_READY]" in stdout:
            # You could add logic here to trigger specific backend events if needed
            pass

        # The prompt says the LAST line is a print() of a markdown table.
        # Let's extract that actual table from stdout.
        
        actual_markdown = self._extract_markdown_table(stdout)
        if actual_markdown:
            cell_data["outputs"] = [{"output_type": "markdown", "data": actual_markdown}]
        
        self.history.append(cell_data)
        return cell_data

    def _extract_markdown_table(self, stdout: str) -> Optional[str]:
        """Extracts the markdown table from the last printed line(s)."""
        if not stdout:
            return None
        # Look for table pattern | ... |
        lines = stdout.strip().splitlines()
        table_lines = []
        in_table = False
        for line in lines:
            if "|" in line and "---" in line:
                in_table = True
            if in_table:
                table_lines.append(line)
        
        return "\n".join(table_lines) if table_lines else stdout.strip()

    def execute_cell(self, markdown_intent: str, python_code: str, metrics_df_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Implements the Three-Phase Cell Architecture (Spec 3).
        Returns the Backend JSON Contract (Spec 4).
        """
        start_time = time.time()
        
        # Phase 1: Markdown Cell is conceptually part of the process, but the return contract 
        # for a "cell" in Spec 4 is a code cell with markdown output.
        
        # Phase 2: Code Cell
        # We wrap the user code with validation and visual gate logic
        
        wrapped_code = f"""
# --- Phase 2: Production Code ---
{python_code}

# --- Phase 3: Visual Gate ---
try:
    _exec_time = {time.time()} - {start_time}
    if '{metrics_df_name}' in locals() or '{metrics_df_name}' in globals():
        _df = {metrics_df_name if metrics_df_name else 'None'}
        _summary = df_info_markdown(_df, title="Execution Summary", execution_time=_exec_time)
    else:
        _summary = f"### ✅ Execution Successful\\n\\n| Metric | Value |\\n| :--- | ---: |\\n| Status | `COMPLETED` |\\n| Time | {{_exec_time:.3f}}s |"
    
    print(f"\\nJSON_OUTPUT_MARKDOWN_START\\n{{_summary}}\\nJSON_OUTPUT_MARKDOWN_END")
except Exception as _e:
    print(f"Visual Gate Error: {{str(_e)}}")
"""

        success, stdout, stderr, _ = self.sandbox.execute(wrapped_code)
        
        if not success:
            return self._handle_recovery(markdown_intent, python_code, stderr)

        # Extract markdown summary
        markdown_data = ""
        match = re.search(r"JSON_OUTPUT_MARKDOWN_START\n(.*?)\nJSON_OUTPUT_MARKDOWN_END", stdout, re.DOTALL)
        if match:
            markdown_data = match.group(1)
            stdout = stdout.replace(match.group(0), "").strip()

        cell_json = {
            "cell_type": "code",
            "source": f"# {markdown_intent}\n\n{python_code}",
            "outputs": [
                {
                    "output_type": "markdown",
                    "data": markdown_data
                }
            ]
        }
        
        self.history.append(cell_json)
        return cell_json

    def _handle_recovery(self, intent: str, code: str, stderr: str) -> Dict[str, Any]:
        """Recovery Protocol (Spec 5)."""
        # Diagnosis logic
        diagnosis = "Unknown Error"
        stderr_lower = stderr.lower()
        if "filenotfounderror" in stderr_lower:
            diagnosis = "File not found. Check relative paths or file existence assertions."
        elif "modulenotfounderror" in stderr_lower:
            diagnosis = "Missing dependency. Ensure all required packages are installed."
        elif "nameerror" in stderr_lower:
            diagnosis = "Variable or function not defined. Check for typos or state persistence issues."
        elif "futurewarning" in stderr_lower or "pandas4warning" in stderr_lower:
            diagnosis = "Deprecation warning or API mismatch detected."
        elif "typeerror" in stderr_lower:
            diagnosis = "Type mismatch. Check function parameters or data types."
        
        recovery_markdown = f"""### ⚠️ Recovery Protocol Triggered

**Original Intent:** {intent}
**Diagnosis:** {diagnosis}

**Traceback:**
```python
{stderr if stderr else 'No traceback captured.'}
```

*Generation halted. Recovery cell required. Fix the issue by updating parameters or logic.*
"""
        return {
            "cell_type": "code",
            "source": code,
            "outputs": [
                {
                    "output_type": "markdown",
                    "data": recovery_markdown
                }
            ]
        }


