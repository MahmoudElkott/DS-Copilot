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
