import os
import json
import re
from typing import Any, Optional

def safe_json_loads(text: str) -> Any:
    try:
        return json.loads(text)
    except Exception:
        block = extract_json_block(text)
        if block:
            try:
                cleaned = block.replace("\n", " ").replace("\t", " ")
                return json.loads(cleaned)
            except Exception as e:
                return {"error": f"json parse fail: {e}", "raw": block}
        return {"error": "no json found", "raw": text}
        
def extract_json_block(text: str) -> Optional[str]:
    match = re.search(r"(\{.*\}|\[.*\])", text, flags=re.S)
    return match.group(1) if match else None