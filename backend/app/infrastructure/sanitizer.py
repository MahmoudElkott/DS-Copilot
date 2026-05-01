# backend/app/infrastructure/sanitizer.py
import logging
import re
from pathlib import Path
from typing import Iterable, List, Tuple

logger = logging.getLogger(__name__)

class CommandSanitizer:
    """Scans agent-generated code for forbidden operations before execution."""

    FORBIDDEN_PATTERNS = [
        (r"os\.remove", "Deletions are restricted"),
        (r"os\.rmdir", "Deletions are restricted"),
        (r"shutil\.rmtree", "Recursive deletions are restricted"),
        (r"os\.system", "Shell execution is restricted"),
        (r"subprocess\.call", "Subprocess execution is restricted"),
        (r"subprocess\.run", "Subprocess execution is restricted"),
        (r"socket\.", "Direct socket manipulation is restricted"),
        (r"requests\.(?:get|post|put|delete|patch)", "Outbound network calls are restricted"),
        (r"urllib\.", "Outbound network calls are restricted"),
        (r"127\.0\.0\.1", "Internal network access is restricted"),
        (r"localhost", "Internal network access is restricted"),
        (r"0\.0\.0\.0", "Internal network access is restricted"),
    ]

    @classmethod
    def sanitize(
        cls,
        code: str,
        allowed_paths: Iterable[str | Path] | None = None,
    ) -> Tuple[bool, List[str]]:
        """
        Checks code against forbidden patterns.
        Returns (is_safe, list_of_violations).
        """
        violations = []
        for pattern, reason in cls.FORBIDDEN_PATTERNS:
            if re.search(pattern, code, re.IGNORECASE):
                violations.append(f"{pattern}: {reason}")

        from app.agent.core.validators.path_validator import PathValidator

        path_result = PathValidator.validate_code(code, allowed_paths=allowed_paths)
        if not path_result.is_safe:
            violations.append(path_result.correction_request)
            violations.extend(path_result.as_messages())
        
        if violations:
            logger.warning(f"[Sanitizer] Code blocked. Violations: {violations}")
            return False, violations
        
        return True, []
