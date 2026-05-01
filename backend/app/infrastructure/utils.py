import uuid
import re
from typing import Dict, List, Any

class CodeSplitter:
    """Utility to parse Agent string output into modular cells."""
    
    @staticmethod
    def parse_cells(text: str, stage: str = "code_writing") -> List[Dict[str, Any]]:
        """
        Parses text for cell delimiters like '### CELL: [NAME]' and returns a list of CodeCell dictionaries.
        If no delimiters are found, returns the entire text as a single cell.
        """
        cells = []
        # Regex matches "### CELL: <name>" and captures the name and the content until the next cell or EOF
        pattern = re.compile(r"### CELL:\s*(.*?)\n(.*?)(?=### CELL:|\Z)", re.DOTALL | re.IGNORECASE)
        
        matches = pattern.finditer(text)
        found = False
        
        for match in matches:
            found = True
            cell_name = match.group(1).strip()
            cell_content = match.group(2).strip()
            
            # Strip markdown code blocks if LLM accidentally wrapped it
            cell_content = re.sub(r"^```python\n", "", cell_content)
            cell_content = re.sub(r"\n```$", "", cell_content)
            cell_content = cell_content.strip()
            
            cells.append({
                "id": str(uuid.uuid4()),
                "type": "code",
                "content": cell_content,
                "metadata": {
                    "stage": stage,
                    "name": cell_name
                }
            })
            
        if not found:
            # Fallback if no delimiters are found
            content = text.strip()
            content = re.sub(r"^```python\n", "", content)
            content = re.sub(r"\n```$", "", content)
            
            cells.append({
                "id": str(uuid.uuid4()),
                "type": "code",
                "content": content.strip(),
                "metadata": {
                    "stage": stage,
                    "name": "main"
                }
            })
            
        return cells
