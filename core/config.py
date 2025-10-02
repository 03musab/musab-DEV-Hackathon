# core/config.py
import os
import dotenv
from typing import Optional
from langchain_cerebras import ChatCerebras
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

dotenv.load_dotenv()

# --- Constants ---
LLM_MODEL = os.environ.get("LLM_MODEL", "llama-3.3-70b")
TEMPERATURE = float(os.environ.get("LLM_TEMPERATURE", "0.2"))
MAX_REFLECTIONS = int(os.environ.get("MAX_REFLECTIONS", "2"))
MEM_COLLECTION = os.environ.get("MEM_COLLECTION", "mini_manus_memory")
EMBED_MODEL = os.environ.get("EMBED_MODEL", "all-MiniLM-L6-v2")
PERSIST_DIR = "./agent_memory"
RAG_PERSIST_DIR = "./rag_docs"
RAG_COLLECTION = "rag_docs"

# --- Global Initializations ---
_llm = ChatCerebras(
    model=LLM_MODEL,
    temperature=TEMPERATURE,
    api_key=os.getenv("API_KEY"),
    streaming=True,
    max_tokens=2048,
    top_p=1
)
_embedding_fn = HuggingFaceEmbeddings(model_name=EMBED_MODEL)
_vectorstore: Optional[Chroma] = None

print("✅ Core config and globals loaded.")