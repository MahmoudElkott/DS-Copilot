# backend/tests/test_agents.py
"""Unit tests for core modules."""
import os
import pytest
from app.utils.helpers import extract_code, safe_json_parse, truncate, sanitize_filename


class TestHelpers:
    def test_extract_code_python_block(self):
        text = "Here is code:\n```python\nprint('hello')\n```\nDone."
        assert extract_code(text) == "print('hello')"

    def test_extract_code_plain_block(self):
        text = "```\nprint('hello')\n```"
        assert extract_code(text) == "print('hello')"

    def test_extract_code_no_block(self):
        text = "print('hello')"
        assert extract_code(text) == "print('hello')"

    def test_safe_json_parse_valid(self):
        assert safe_json_parse('{"a": 1}') == {"a": 1}

    def test_safe_json_parse_embedded(self):
        text = 'Some text\n{"result": true}\nMore text'
        assert safe_json_parse(text) == {"result": True}

    def test_safe_json_parse_invalid(self):
        assert safe_json_parse("not json", "default") == "default"

    def test_safe_json_parse_last_line(self):
        text = "Log line 1\nLog line 2\n{\"key\": \"value\"}"
        assert safe_json_parse(text) == {"key": "value"}

    def test_truncate(self):
        assert truncate("hello world", 5) == "he..."
        assert truncate("hi", 10) == "hi"
        assert truncate("", 5) == ""

    def test_sanitize_filename(self):
        assert sanitize_filename("my:file?.csv") == "my_file_.csv"
        assert sanitize_filename("normal.csv") == "normal.csv"


class TestExecutionResult:
    def test_creation(self):
        from app.infrastructure.executor import ExecutionResult
        r = ExecutionResult(success=True, stdout="ok", stderr="")
        assert r.success is True
        assert r.files_created == []

    def test_failure(self):
        from app.infrastructure.executor import ExecutionResult
        r = ExecutionResult(success=False, stdout="", stderr="error", execution_time=1.5)
        assert r.success is False
        assert r.execution_time == 1.5


class TestHarnessReport:
    def test_creation(self):
        from app.infrastructure.harness import HarnessReport
        r = HarnessReport(step_name="test_step")
        assert r.status == "pending"
        assert r.tests_passed == 0
        assert r.errors == []


class TestFileManager:
    def test_create_project_structure(self, temp_dir):
        from app.infrastructure.file_manager import FileManager
        fm = FileManager(output_dir=temp_dir)
        project_dir = fm.create_project_structure("test-project")
        assert os.path.isdir(project_dir)
        assert os.path.isdir(os.path.join(project_dir, "src"))
        assert os.path.isdir(os.path.join(project_dir, "tests"))
        assert os.path.isdir(os.path.join(project_dir, "data", "raw"))

    def test_write_file(self, temp_dir):
        from app.infrastructure.file_manager import FileManager
        fm = FileManager(output_dir=temp_dir)
        project_dir = fm.create_project_structure("test-project")
        path = fm.write_file(project_dir, "test.txt", "hello")
        assert os.path.exists(path)
        with open(path) as f:
            assert f.read() == "hello"

    def test_generate_readme(self):
        from app.infrastructure.file_manager import FileManager
        fm = FileManager()
        readme = fm.generate_readme({"name": "Test", "task_type": "classification"})
        assert "Test" in readme
        assert "classification" in readme

    def test_generate_requirements(self):
        from app.infrastructure.file_manager import FileManager
        fm = FileManager()
        reqs = fm.generate_requirements(["custom-pkg>=1.0"])
        assert "pandas" in reqs
        assert "custom-pkg>=1.0" in reqs
