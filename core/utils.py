# core/utils.py
import json
import re
from typing import Any, Optional

def extract_json_block(text: str) -> Optional[str]:
    """Extracts the first JSON object or array from a string."""
    match = re.search(r"(\{.*\}|\[.*\])", text, flags=re.S)
    return match.group(1) if match else None

def safe_json_loads(text: str) -> Any:
    """Safely parses a JSON string, even if it's embedded in other text."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        block = extract_json_block(text)
        if block:
            try:
                return json.loads(block)
            except json.JSONDecodeError:
                return {"error": "json parse fail", "raw": block}
        return {"error": "no json found", "raw": text}