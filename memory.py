# memory.py

from typing import Dict, Any, List
from globals import _vectorstore

def mem_add(text: str, kind: str = "note"):
    if _vectorstore:
        try:
            _vectorstore.add_texts([f"{kind}: {text}"])
            print(f"🧠 Memory Add Request Sent: '{kind}: {text[:60]}...'")
        except Exception as e:
            print(f"❌ Memory Add Failed: {e}")

def mem_recall(query: str, k: int = 3):
    """Recalls k most similar documents from the vector store."""
    if _vectorstore:
        docs = _vectorstore.similarity_search(query, k=k)
        return [d.page_content for d in docs]
    return []