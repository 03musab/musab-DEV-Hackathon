import os
import json
import ast
import subprocess

from typing import Dict, Any, List
from ddgs import DDGS

# Note: These tools are self-contained and don't need to import from other project files.

def tool_web_search(query: str, max_results: int = 5) -> Dict[str, Any]:
    results: List[Dict[str, Any]] = []
    try:
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                results.append({
                    "title": r.get("title"),
                    "href": r.get("href"),
                    "body": r.get("body"),
                })
    except Exception as e:
        return {"error": f"search_failed: {e}"}
    return {"results": results}

class _MathVisitor(ast.NodeVisitor):
    allowed_nodes = (
        ast.Expression, ast.BinOp, ast.UnaryOp, ast.Num, ast.Load,
        ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Mod, ast.Pow,
        ast.USub, ast.UAdd, ast.FloorDiv
    )
    def visit(self, node):
        if not isinstance(node, self.allowed_nodes):
            raise ValueError(f"disallowed expression: {type(node).__name__}")
        return super().visit(node)

def tool_calculator(expression: str) -> Dict[str, Any]:
    try:
        node = ast.parse(expression, mode="eval")
        _MathVisitor().visit(node)
        value = eval(compile(node, "<calc>", "eval"), {"__builtins__": {}}, {})
        return {"ok": True, "result": value}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ===============================================================
# ✅ Update tool_rag_search to always use the latest persisted DB
# ===============================================================

# New tools for the coding agent
def tool_write_file(file_path: str, content: str) -> Dict[str, Any]:
    """Writes content to a file in the sandbox environment."""
    try:
        with open(file_path, "w") as f:
            f.write(content)
        return {"status": "success", "message": f"Wrote to file: {file_path}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def tool_read_file(file_path: str) -> Dict[str, Any]:
    """Reads content from a file in the sandbox environment."""
    try:
        with open(file_path, "r") as f:
            content = f.read()
        return {"status": "success", "content": content}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def tool_run_code(command: str) -> Dict[str, Any]:
    """Executes a shell command in the sandbox and returns output."""
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        return {
            "status": "success",
            "output": result.stdout,
            "error": result.stderr if result.stderr else None
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
    
