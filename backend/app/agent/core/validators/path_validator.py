"""AST-based path validation for generated code."""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

from app.agent.tools.file_handler import FileHandler


_PATH_HINT_TARGETS = (
    "path",
    "file",
    "dir",
    "output",
    "artifact",
    "model",
    "plot",
    "report",
    "csv",
    "json",
)

_PATH_CONSUMING_CALLS = {
    "open",
    "read_csv",
    "read_excel",
    "read_json",
    "read_parquet",
    "to_csv",
    "to_excel",
    "to_json",
    "savefig",
    "mkdir",
    "makedirs",
    "touch",
    "write_text",
    "write_bytes",
    "unlink",
    "remove",
    "rename",
    "replace",
    "load",
    "dump",
}


@dataclass(frozen=True)
class PathViolation:
    literal: str
    line: int
    column: int
    resolved_path: str
    reason: str

    def format_message(self) -> str:
        location = f"line {self.line}:{self.column}" if self.line else "unknown location"
        return (
            f"{location} literal {self.literal!r} resolves to {self.resolved_path!r} "
            f"outside allowed paths ({self.reason})"
        )


@dataclass(frozen=True)
class PathValidationResult:
    is_safe: bool
    violations: tuple[PathViolation, ...] = ()
    allowed_paths: tuple[str, ...] = ()
    correction_request: str = ""

    def as_messages(self) -> list[str]:
        return [violation.format_message() for violation in self.violations]


class PathValidator:
    """Validate that generated code only references approved file-system paths."""

    @staticmethod
    def _normalize_allowed_paths(allowed_paths: Iterable[str | Path] | None) -> tuple[Path, ...]:
        resolved: list[Path] = []
        for path in allowed_paths or []:
            if path is None:
                continue
            try:
                resolved_path = Path(path).expanduser().resolve()
            except Exception:
                continue
            if resolved_path not in resolved:
                resolved.append(resolved_path)
        return tuple(sorted(resolved, key=str))

    @staticmethod
    def _is_safe_url(value: str) -> bool:
        return bool(re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", value))

    @classmethod
    def _looks_like_path(cls, value: str) -> bool:
        if not value or cls._is_safe_url(value):
            return False
        if re.match(r"^[A-Za-z]:[\\/]", value):
            return True
        if value.startswith(("~", ".", "..")):
            return True
        if "/" in value or "\\" in value:
            return True
        suffix = Path(value).suffix
        return bool(suffix and not value.strip().startswith("{"))

    @staticmethod
    def _get_call_name(node: ast.AST) -> str:
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            prefix = PathValidator._get_call_name(node.value)
            return f"{prefix}.{node.attr}" if prefix else node.attr
        return ""

    @classmethod
    def _target_name_looks_like_path(cls, target: ast.AST) -> bool:
        if not isinstance(target, ast.Name):
            return False
        lowered = target.id.lower()
        return any(marker in lowered for marker in _PATH_HINT_TARGETS)

    @classmethod
    def _collect_candidates(cls, tree: ast.AST) -> list[tuple[str, int, int]]:
        candidates: list[tuple[str, int, int]] = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                if cls._looks_like_path(node.value):
                    candidates.append((node.value, getattr(node, "lineno", 0), getattr(node, "col_offset", 0)))
                continue

            if isinstance(node, ast.Assign) and len(node.targets) == 1 and cls._target_name_looks_like_path(node.targets[0]):
                if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                    candidates.append((node.value.value, getattr(node, "lineno", 0), getattr(node, "col_offset", 0)))
                elif isinstance(node.value, ast.Call):
                    candidates.extend(cls._collect_call_candidates(node.value))
                continue

            if isinstance(node, ast.AnnAssign) and cls._target_name_looks_like_path(node.target):
                value = node.value
                if isinstance(value, ast.Constant) and isinstance(value.value, str):
                    candidates.append((value.value, getattr(node, "lineno", 0), getattr(node, "col_offset", 0)))
                elif isinstance(value, ast.Call):
                    candidates.extend(cls._collect_call_candidates(value))
                continue

            if isinstance(node, ast.Call):
                candidates.extend(cls._collect_call_candidates(node))

        return candidates

    @classmethod
    def _collect_call_candidates(cls, node: ast.Call) -> list[tuple[str, int, int]]:
        call_name = cls._get_call_name(node.func)
        candidates: list[tuple[str, int, int]] = []

        if call_name.endswith("join") and node.args:
            parts: list[str] = []
            for arg in node.args:
                if not isinstance(arg, ast.Constant) or not isinstance(arg.value, str):
                    break
                parts.append(arg.value)
            else:
                if parts:
                    candidates.append((str(Path(*parts)), getattr(node, "lineno", 0), getattr(node, "col_offset", 0)))

        if call_name.split(".")[-1] in _PATH_CONSUMING_CALLS and node.args:
            first_arg = node.args[0]
            if isinstance(first_arg, ast.Constant) and isinstance(first_arg.value, str):
                candidates.append((first_arg.value, getattr(first_arg, "lineno", 0), getattr(first_arg, "col_offset", 0)))

        return candidates

    @staticmethod
    def _is_under_allowed_root(candidate: Path, allowed_roots: Sequence[Path]) -> bool:
        resolved_candidate = candidate.resolve(strict=False)
        for root in allowed_roots:
            resolved_root = root.resolve(strict=False)
            if resolved_candidate == resolved_root or resolved_root in resolved_candidate.parents:
                return True
        return False

    @classmethod
    def _validate_literal(
        cls,
        literal: str,
        line: int,
        column: int,
        allowed_roots: Sequence[Path],
    ) -> PathViolation | None:
        if not cls._looks_like_path(literal):
            return None

        candidate = Path(literal).expanduser()
        if candidate.is_absolute():
            if cls._is_under_allowed_root(candidate, allowed_roots):
                return None
            return PathViolation(
                literal=literal,
                line=line,
                column=column,
                resolved_path=str(candidate.resolve(strict=False)),
                reason="absolute path escapes the allowed roots",
            )

        for root in allowed_roots:
            resolved = (root / candidate).resolve(strict=False)
            if cls._is_under_allowed_root(resolved, allowed_roots):
                return None

        base_root = allowed_roots[0] if allowed_roots else Path.cwd()
        return PathViolation(
            literal=literal,
            line=line,
            column=column,
            resolved_path=str((base_root / candidate).resolve(strict=False)),
            reason="relative path does not resolve inside any allowed root",
        )

    @classmethod
    def validate_code(
        cls,
        code: str,
        allowed_paths: Iterable[str | Path] | None = None,
    ) -> PathValidationResult:
        try:
            tree = ast.parse(code)
        except SyntaxError as exc:
            violation = PathViolation(
                literal="<syntax-error>",
                line=exc.lineno or 0,
                column=(exc.offset or 0) - 1 if exc.offset else 0,
                resolved_path="",
                reason=f"invalid syntax: {exc.msg}",
            )
            return PathValidationResult(
                is_safe=False,
                violations=(violation,),
                correction_request="Path Correction Request: generated code could not be parsed before validation.",
            )

        allowed_roots = cls._normalize_allowed_paths(allowed_paths or FileHandler.get_allowed_paths())
        candidates = cls._collect_candidates(tree)

        violations: list[PathViolation] = []
        seen: set[tuple[str, int, int]] = set()
        for literal, line, column in candidates:
            key = (literal, line, column)
            if key in seen:
                continue
            seen.add(key)

            violation = cls._validate_literal(literal, line, column, allowed_roots)
            if violation is not None:
                violations.append(violation)

        if not violations:
            return PathValidationResult(is_safe=True, allowed_paths=tuple(str(path) for path in allowed_roots))

        allowed_list = ", ".join(str(path) for path in allowed_roots) or "<none>"
        correction_lines = [violation.format_message() for violation in violations]
        correction_request = (
            "Path Correction Request: generated code references paths outside the allowed roots. "
            f"Allowed roots: {allowed_list}. "
            + " | ".join(correction_lines)
        )
        return PathValidationResult(
            is_safe=False,
            violations=tuple(violations),
            correction_request=correction_request,
        )


__all__ = ["PathValidationResult", "PathValidator", "PathViolation"]