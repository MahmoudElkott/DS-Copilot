import os

from app.agent.core.validators.path_validator import PathValidator


class TestPathValidator:
    def test_allows_path_inside_allowed_root(self, tmp_path):
        allowed_root = tmp_path / "storage"
        allowed_root.mkdir()

        code = """
from pathlib import Path

output_path = "storage/models/model.pkl"
Path(output_path).parent.mkdir(parents=True, exist_ok=True)
"""

        result = PathValidator.validate_code(code, allowed_paths=[allowed_root])
        assert result.is_safe is True
        assert result.violations == ()

    def test_blocks_path_outside_allowed_root(self, tmp_path):
        allowed_root = tmp_path / "storage"
        allowed_root.mkdir()

        unsafe_path = "C:/Windows/System32/drivers/etc/hosts" if os.name == "nt" else "/etc/passwd"
        code = f"open({unsafe_path!r}, 'r', encoding='utf-8')"

        result = PathValidator.validate_code(code, allowed_paths=[allowed_root])
        assert result.is_safe is False
        assert result.violations
        assert "Path Correction Request" in result.correction_request