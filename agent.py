# agent.py
from __future__ import annotations
import os
from typing import List, Dict, Any

# Import the new Cerebras SDK
from cerebras.cloud.sdk import Cerebras

# The old LangGraph and other imports are no longer needed for the simplified agent
"""
from langchain_community.document_loaders import (
    TextLoader, PyPDFLoader, CSVLoader, UnstructuredExcelLoader,
    UnstructuredPowerPointLoader, UnstructuredWordDocumentLoader
)

from core.config import (
    _llm, _embedding_fn, RAG_PERSIST_DIR, RAG_COLLECTION,
    MAX_REFLECTIONS
""" # End of old, unused code

# --- Knowledge Base Ingestion ---

# code for storing or uploading the data 
def ingest_knowledge_base(file_path: str):
    """
    Ingests a user-uploaded file (txt, pdf, csv, excel, ppt, docx).
    """
    print(f"📂 Ingesting file: {file_path}")

    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".txt":
        loader = TextLoader(file_path, encoding="utf-8")
    elif ext == ".pdf":
        loader = PyPDFLoader(file_path)
    elif ext == ".csv":
        loader = CSVLoader(file_path)
    elif ext in [".xls", ".xlsx"]:
        loader = UnstructuredExcelLoader(file_path)
    elif ext in [".ppt", ".pptx"]:
        loader = UnstructuredPowerPointLoader(file_path)
    elif ext in [".doc", ".docx"]:
        loader = UnstructuredWordDocumentLoader(file_path)
    else:
        raise ValueError(f"❌ Unsupported file type: {ext}")

    documents = loader.load()
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = text_splitter.split_documents(documents)
    
    print(f"✅ File split into {len(chunks)} chunks.")

    rag_db = Chroma.from_documents(
        documents=chunks,
        embedding=_embedding_fn,
        persist_directory=RAG_PERSIST_DIR,
        collection_name=RAG_COLLECTION
    )
    print("✅ Knowledge base updated and saved.")
    return f"File '{file_path}' ingested successfully!"

# --- Main Agent Runner ---

def run_agent_once(user_input: str, history: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Runs a simplified agent that directly calls the Cerebras model.
    This replaces the complex LangGraph agent for this specific workflow.
    """
    try:
        client = Cerebras(api_key=os.environ.get("CEREBRAS_API_KEY"))

        # Combine history and the new user input for the model
        messages = [{"role": "system", "content": "You are a helpful assistant."}]
        for item in history:
            # Assuming history items have 'role' and 'content'
            messages.append(item)
        messages.append({"role": "user", "content": user_input})

        stream = client.chat.completions.create(
            messages=messages,
            model="llama-3.3-70b",
            stream=True,
            max_completion_tokens=2048,
            temperature=0.2,
            top_p=1
        )

        # Since the backend doesn't stream to the frontend, we collect the full response
        full_response = ""
        for chunk in stream:
            full_response += chunk.choices[0].delta.content or ""

        return {
            "final": full_response or "The agent processed the request but returned no content.",
            "log": ["Agent task completed using direct Cerebras call."]
        }

    except Exception as e:
        print(f"❌ Error in simplified agent: {e}")
        return {
            "final": f"An error occurred while processing your request: {e}",
            "log": [f"Error: {e}"]
        }