# tools.py
# This file centralizes the definition of all agent tools.
from __future__ import annotations
from typing import Dict, Any, List

from langchain_chroma import Chroma
from ddgs import DDGS

# Import helper functions from utils.py
from utils import tool_web_search, tool_calculator

# Imports from your globals file
from globals import _embedding_fn, RAG_PERSIST_DIR, RAG_COLLECTION


def tool_rag_search(query: str) -> Dict[str, Any]:
    try:
        rag_db = Chroma(
            persist_directory=RAG_PERSIST_DIR,
            embedding_function=_embedding_fn,
            collection_name=RAG_COLLECTION
        )
        docs = rag_db.similarity_search(query, k=3)
        results_text = "\n---\n".join([d.page_content for d in docs])
        return {"results": results_text or "No relevant info found in the uploaded file."}
    except Exception as e:
        return {"error": f"rag_search_failed: {e}"}

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
       "desc": "Use this tool to answer questions about specific facts or entities found in an uploaded document. It should be used for details about people, companies, or concepts mentioned in the knowledge base.",
        "func": lambda args: tool_rag_search(args.get("query", ""))
    },
    "python_repl": {
        "desc": "A Python shell. Use this for complex math, data analysis, or executing any Python code. Input should be a valid Python command. The result is what is printed to standard output.",
        "func": lambda args: {
            "ok": True,
            "result": "Python REPL not implemented in this script."
        }
    }
}