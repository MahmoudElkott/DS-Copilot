import re
from typing import List, Dict

# ── Regex to split LLM output into markdown + code blocks ──
_FENCED_BLOCK_RE = re.compile(
    r"(```(?:python|py)?\s*\n[\s\S]*?```)",
    re.IGNORECASE,
)

_CODE_CONTENT_RE = re.compile(
    r"```(?:python|py)?\s*\n([\s\S]*?)```",
    re.IGNORECASE,
)

def split_into_cells(text: str) -> List[Dict[str, str]]:
    """
    Split LLM output into an alternating sequence of markdown and code cells.
    Returns a list of dicts: [{"type": "markdown"|"code", "content": "..."}]
    """
    cells = []
    # Split text by fenced code blocks, keeping the delimiters
    parts = _FENCED_BLOCK_RE.split(text)

    for part in parts:
        if not part.strip():
            continue

        # Check if this part is a code block
        code_match = _CODE_CONTENT_RE.match(part.strip())
        if code_match:
            cells.append({
                "type": "code",
                "content": code_match.group(1).strip(),
            })
        else:
            # It's markdown text
            cells.append({
                "type": "markdown",
                "content": part.strip(),
            })

    return cells
