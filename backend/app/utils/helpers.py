# backend/app/utils/helpers.py
"""
Shared utility functions used across the application.
"""
import json
import re
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


def extract_code(text: str) -> str:
    """
    Extract Python code from markdown code blocks.
    Handles ```python ... ``` and plain ``` ... ``` blocks.
    """
    if "```python" in text:
        parts = text.split("```python")
        if len(parts) > 1:
            code = parts[1].split("```")[0]
            return code.strip()
    if "```" in text:
        parts = text.split("```")
        if len(parts) > 1:
            # Skip the language identifier if present on first line
            code_block = parts[1]
            lines = code_block.split("\n")
            # If first line looks like a language identifier, skip it
            if lines and lines[0].strip() in ("python", "py", "json", "bash", "sh", ""):
                code_block = "\n".join(lines[1:])
            return code_block.strip()
    return text.strip()


def safe_json_parse(text: str, default: Any = None) -> Any:
    """
    Safely parse JSON from text.
    Tries to find JSON in the text, handles common issues.
    """
    if not text:
        return default

    # Try direct parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try to find JSON object in text
    try:
        # Look for { ... } pattern
        match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', text, re.DOTALL)
        if match:
            return json.loads(match.group())
    except (json.JSONDecodeError, AttributeError):
        pass

    # Try to find JSON array in text
    try:
        match = re.search(r'\[.*\]', text, re.DOTALL)
        if match:
            return json.loads(match.group())
    except (json.JSONDecodeError, AttributeError):
        pass

    # Try last line (common pattern: agents print JSON as last line)
    try:
        lines = text.strip().split("\n")
        for line in reversed(lines):
            line = line.strip()
            if line.startswith("{") or line.startswith("["):
                return json.loads(line)
    except (json.JSONDecodeError, IndexError):
        pass

    logger.warning(f"Failed to parse JSON from text: {text[:200]}...")
    return default


def truncate(text: str, max_len: int = 500, suffix: str = "...") -> str:
    """Safely truncate text to max_len characters."""
    if not text:
        return ""
    if len(text) <= max_len:
        return text
    return text[: max_len - len(suffix)] + suffix


def _compact_value_for_prompt(value: Any, max_items: int, max_depth: int) -> Any:
    """Recursively compact nested collections for prompt safety."""
    if max_depth <= 0:
        if isinstance(value, dict):
            return f"<dict with {len(value)} items>"
        if isinstance(value, (list, tuple, set)):
            return f"<{type(value).__name__} with {len(value)} items>"
        return value

    if isinstance(value, dict):
        compacted = {}
        items = list(value.items())
        for idx, (key, item_value) in enumerate(items):
            if idx >= max_items:
                compacted["__omitted_items__"] = len(items) - max_items
                break
            compacted[str(key)] = _compact_value_for_prompt(
                item_value,
                max_items=max_items,
                max_depth=max_depth - 1,
            )
        return compacted

    if isinstance(value, (list, tuple, set)):
        seq = list(value)
        compacted = [
            _compact_value_for_prompt(
                item,
                max_items=max_items,
                max_depth=max_depth - 1,
            )
            for item in seq[:max_items]
        ]
        if len(seq) > max_items:
            compacted.append(f"... {len(seq) - max_items} more items omitted")
        return compacted

    return value


def compact_json_for_prompt(
    data: Any,
    max_chars: int = 8000,
    max_items: int = 40,
    max_depth: int = 3,
) -> str:
    """
    Convert arbitrary JSON-like data into a compact, prompt-safe JSON string.

    The function keeps the most informative structure while trimming deeply nested
    or very large collections so LLM requests stay within model context windows.
    """
    reduced = data
    if isinstance(data, dict):
        reduced = dict(data)
        # Always drop known high-volume keys to keep prompts predictable.
        heavy_keys = (
            "sample_data",
            "describe",
            "raw_rows",
            "raw_data",
            "full_output",
            "stdout",
            "stderr",
            "messages",
            "logs",
        )
        omitted = {}
        for key in heavy_keys:
            if key in reduced:
                value = reduced.pop(key)
                size = len(value) if hasattr(value, "__len__") else 1
                omitted[key] = f"omitted ({size} items)"
        if omitted:
            reduced["__omitted_heavy_keys__"] = omitted

    try:
        text = json.dumps(reduced, indent=2, default=str)
    except TypeError:
        text = str(reduced)

    if len(text) <= max_chars:
        return text

    reduced = _compact_value_for_prompt(
        reduced,
        max_items=max_items,
        max_depth=max_depth,
    )

    try:
        compacted_text = json.dumps(reduced, indent=2, default=str)
    except TypeError:
        compacted_text = str(reduced)

    if len(compacted_text) <= max_chars:
        return compacted_text

    if isinstance(data, dict):
        minimal = {
            "shape": data.get("shape"),
            "columns_count": len(data.get("columns", [])) if isinstance(data.get("columns"), list) else None,
            "numeric_columns_count": len(data.get("numeric_columns", [])) if isinstance(data.get("numeric_columns"), list) else None,
            "categorical_columns_count": len(data.get("categorical_columns", [])) if isinstance(data.get("categorical_columns"), list) else None,
            "duplicates": data.get("duplicates"),
            "memory_usage_mb": data.get("memory_usage_mb"),
            "null_columns_count": len(
                [
                    col
                    for col, count in (data.get("null_counts") or {}).items()
                    if count
                ]
            ) if isinstance(data.get("null_counts"), dict) else None,
        }
        return json.dumps(minimal, indent=2, default=str)

    fallback = {"summary": truncate(str(data), max_len=max_chars - 30)}
    return json.dumps(fallback, indent=2, default=str)


def format_execution_time(seconds: float) -> str:
    """Format execution time as human-readable string."""
    if seconds < 1:
        return f"{seconds * 1000:.0f}ms"
    elif seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = seconds % 60
        return f"{minutes}m {secs:.0f}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h {minutes}m"


def sanitize_filename(name: str) -> str:
    """Sanitize a string for use as a filename."""
    # Remove or replace invalid characters
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', name)
    sanitized = sanitized.strip('. ')
    # Limit length
    if len(sanitized) > 200:
        sanitized = sanitized[:200]
    return sanitized or "unnamed"


def merge_dicts(base: dict, override: dict) -> dict:
    """Deep merge two dictionaries. Override values take precedence."""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_dicts(result[key], value)
        else:
            result[key] = value
    return result
