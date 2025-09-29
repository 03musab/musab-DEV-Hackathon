# globals.py
# This file centralizes all global variables to prevent circular imports.
from __future__ import annotations
import os
import dotenv
from typing import Optional
from langchain_cerebras import ChatCerebras
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_chroma import Chroma

dotenv.load_dotenv()

LLM_MODEL = os.environ.get("LLM_MODEL", "llama-4-scout-17b-16e-instruct")
TEMPERATURE = float(os.environ.get("LLM_TEMPERATURE", "0"))
MAX_REFLECTIONS = int(os.environ.get("MAX_REFLECTIONS", "2"))
MEM_COLLECTION = os.environ.get("MEM_COLLECTION", "mini_manus_memory")
EMBED_MODEL = os.environ.get("EMBED_MODEL", "all-MiniLM-L6-v2")
PERSIST_DIR = "/kaggle/working/agent_memory"
RAG_PERSIST_DIR = "/kaggle/working/"
RAG_COLLECTION = "rag_docs"

_llm = ChatCerebras(
    model=LLM_MODEL,
    temperature=TEMPERATURE,
    api_key=os.getenv("API_KEY")
)
_embedding_fn = HuggingFaceEmbeddings(model_name=EMBED_MODEL)
_vectorstore: Optional[Chroma] = None

print("Global variables loaded ✅")