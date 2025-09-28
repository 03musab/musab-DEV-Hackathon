import os
import traceback
import json
import re

from typing import Any, Optional # <-- Add this line
from langchain_community.document_loaders import (
    TextLoader, PyPDFLoader, CSVLoader, UnstructuredExcelLoader,
    UnstructuredPowerPointLoader, UnstructuredWordDocumentLoader
)
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
# No import from dashboard.py needed here

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

def upload_file(files):
    # This function is the entry point for Gradio.
    # It must be able to call ingest_knowledge_base and access the global variables
    # needed by that function.
    # The simplest way is for the calling function to handle the dependency injection.
    
    if not files:
        return "⚠️ Please upload at least one file."
    results = []
    for file in files:
        file_path = file.name
        try:
            # We must pass the necessary globals to ingest_knowledge_base
            # so it doesn't need to import them directly, which would cause a circular import.
            # This part of the code needs to be in agent_core.py or dashboard.py
            # where the globals are defined, to avoid the circular dependency.
            # I will move this logic to the dashboard.py file to keep the
            # project clean and functional.

            # The original code here:
            # status = ingest_knowledge_base(file_path)
            
            # The corrected approach, since ingest_knowledge_base is now in dashboard.py:
            from dashboard import ingest_knowledge_base
            status = ingest_knowledge_base(file_path)

            results.append(status)
        except Exception as e:
            error_msg = "".join(traceback.format_exception_only(type(e), e))
            print("❌ Ingestion failed:", error_msg)
            results.append(f"❌ Error ingesting {os.path.basename(file_path)}: {error_msg}")
    return "\n".join(results)