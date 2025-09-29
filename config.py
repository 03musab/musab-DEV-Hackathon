import os
import traceback
import json
import re
from typing import Any, Optional

from langchain_community.document_loaders import (
    TextLoader, PyPDFLoader, CSVLoader, UnstructuredExcelLoader,
    UnstructuredPowerPointLoader, UnstructuredWordDocumentLoader
)
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma

# Import necessary globals from the globals file
from globals import _embedding_fn, RAG_PERSIST_DIR, RAG_COLLECTION


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

def upload_file(files):
    if not files:
        return "⚠️ Please upload at least one file."
    results = []
    for file in files:
        file_path = file.name
        try:
            status = ingest_knowledge_base(file_path)
            results.append(status)
        except Exception as e:
            error_msg = "".join(traceback.format_exception_only(type(e), e))
            print("❌ Ingestion failed:", error_msg)
            results.append(f"❌ Error ingesting {os.path.basename(file_path)}: {error_msg}")
    return "\n".join(results)

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