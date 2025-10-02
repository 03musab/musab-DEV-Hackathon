# tools.py
# This file centralizes the definition of all agent tools.
from __future__ import annotations
import os
import ast
import subprocess
from typing import Dict, Any, List

from langchain_chroma import Chroma
from ddgs import DDGS

# Imports from your core module
from core.config import _embedding_fn, RAG_PERSIST_DIR, RAG_COLLECTION

# --- Tool Implementations (formerly utils.py) ---

def tool_web_search(query: str, max_results: int = 3) -> Dict[str, Any]:
    """Searches the web for a given query."""
    results: List[Dict[str, Any]] = []
    try:
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                results.append({"title": r.get("title"), "href": r.get("href"), "body": r.get("body")})
    except Exception as e:
        return {"error": f"search_failed: {e}"}
    return {"results": results}

class _MathVisitor(ast.NodeVisitor):
    allowed_nodes = (ast.Expression, ast.BinOp, ast.UnaryOp, ast.Num, ast.Load, ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Mod, ast.Pow, ast.USub, ast.UAdd, ast.FloorDiv)
    def visit(self, node):
        if not isinstance(node, self.allowed_nodes):
            raise ValueError(f"disallowed expression: {type(node).__name__}")
        return super().visit(node)

def tool_calculator(expression: str) -> Dict[str, Any]:
    """Evaluates a safe arithmetic expression."""
    try:
        node = ast.parse(expression, mode="eval")
        _MathVisitor().visit(node)
        value = eval(compile(node, "<calc>", "eval"), {"__builtins__": {}}, {})
        return {"ok": True, "result": value}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def tool_write_file(file_path: str, content: str) -> Dict[str, Any]:
    """Writes content to a file."""
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        return {"status": "success", "message": f"Wrote to file: {file_path}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def tool_read_file(file_path: str) -> Dict[str, Any]:
    """Reads content from a file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        return {"status": "success", "content": content}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def tool_run_code(command: str) -> Dict[str, Any]:
    """Executes a shell command and returns its output."""
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, check=False)
        return {"status": "success", "output": result.stdout, "error": result.stderr if result.stderr else None}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def tool_rag_search(query: str, source_file: str | None = None) -> Dict[str, Any]:
    try:
        rag_db = Chroma(
            persist_directory=RAG_PERSIST_DIR,
            embedding_function=_embedding_fn,
            collection_name=RAG_COLLECTION
        )
        
        search_kwargs = {"k": 3}
        if source_file:
            # We need to construct the full path as stored in Chroma's metadata
            full_path = os.path.join("uploads", source_file)
            search_kwargs["filter"] = {"source": full_path}
            print(f"🔍 RAG search filtered by source: {full_path}")

        docs = rag_db.similarity_search(query, **search_kwargs)
        results_text = "\n---\n".join([d.page_content for d in docs])
        return {"results": results_text or "No relevant info found in the uploaded file."}
    except Exception as e:
        return {"error": f"rag_search_failed: {e}"}

def _get_coding_agent_tool():
    from coding import tool_coding_agent
    return tool_coding_agent

# --- Tool Definitions ---

TOOLS = {
    "web_search": {
        "desc": "Search the web for general information, current events, or real-world people and places.",
        "func": lambda args: tool_web_search(args.get("query", ""), int(args.get("max_results", 3)))
    },
    "calculator": {
        "desc": "Evaluate arithmetic expressions.",
        "func": lambda args: tool_calculator(args.get("expression", ""))
    },
    "rag_search": {
        "desc": "Use this tool to answer questions about specific facts or entities found in an uploaded document. If the user has selected a specific file, you MUST use the `source_file` argument with the filename.",
        "func": lambda args: tool_rag_search(args.get("query", ""), args.get("source_file"))
    },
    "python_repl": {
        "desc": "A Python shell. Use this for complex math, data analysis, or executing any Python code. Input should be a valid Python command. The result is what is printed to standard output.",
        "func": lambda args: {
            "ok": True,
            "result": "Python REPL not implemented in this script."
        }
    },
    "coding_agent_tool": {
        "desc": "A specialized agent for writing, executing, and debugging code. Use this for all coding-related tasks.",
        "func": lambda args: _get_coding_agent_tool()(args.get("user_input", ""))
    }
}