# backend/tests/conftest.py
"""
Pytest fixtures for DS-Copilot tests.
"""
import os
import sys
import pytest
import tempfile

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


@pytest.fixture
def sample_csv_path():
    """Path to the sample Iris dataset."""
    return os.path.join(os.path.dirname(__file__), "fixtures", "sample_data.csv")


@pytest.fixture
def temp_dir():
    """Temporary directory for test outputs."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def mock_settings(monkeypatch, temp_dir):
    """Override settings for testing."""
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{os.path.join(temp_dir, 'test.db')}")
    monkeypatch.setenv("LOCAL_SANDBOX_DIR", os.path.join(temp_dir, "sandbox"))
    monkeypatch.setenv("OUTPUT_DIR", os.path.join(temp_dir, "output"))
    monkeypatch.setenv("OPENAI_API_KEY", "")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
    monkeypatch.setenv("GOOGLE_API_KEY", "")


@pytest.fixture
def mock_llm_router():
    """Create a mock LLM router that returns predefined responses."""
    from tests.mocks.mock_llm import MockLLMRouter
    return MockLLMRouter()
