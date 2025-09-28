def ingest_knowledge_base(file_path: str):
    """
    Ingests a user-uploaded file (txt, pdf, csv, excel, ppt, docx).
    """
    print(f"📂 Ingesting file: {file_path}")

    # Pick loader based on file extension
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

    # Load documents
    documents = loader.load()

    # Split into chunks
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = text_splitter.split_documents(documents)
    
    print(f"✅ File split into {len(chunks)} chunks.")

    # Update vector store
    rag_db = Chroma.from_documents(
        documents=chunks,
        embedding=_embedding_fn,
        persist_directory=RAG_PERSIST_DIR,
        collection_name=RAG_COLLECTION
    )

    print("✅ Knowledge base updated and saved.")
    return f"File '{file_path}' ingested successfully!"


# ------------------------
# Memory helpers
# ------------------------

def mem_recall(query: str, k: int = 3):
    """Recalls k most similar documents from the vector store."""
    docs = _vectorstore.similarity_search(query, k=k)
    return [d.page_content for d in docs]

# Place this with your other node functions

# Replace your global DIRECT_ANSWER_SYS variable with this:

DIRECT_ANSWER_SYS = """
You are a helpful assistant that answers questions ONLY from the provided memory context.
The memory may contain structured facts in JSON format, like {"entity": "user", "attribute": "name", "value": "haad"}.

- To answer the user's question, you MUST parse these JSON facts.
- When asked 'what is my name' or about the 'user', look for facts where 'entity' is 'user'.
- When asked 'what is your name' or about the 'agent', look for facts where 'entity' is 'agent'.
- Use this information to answer precisely. Do not mention the JSON structure in your answer.

- If the memory does NOT contain enough information to answer, you MUST respond with the exact phrase: 'NO_DIRECT_ANSWER' and nothing else.
"""

def extract_json_block(text: str) -> Optional[str]:
    import re
    match = re.search(r"(\{.*\}|\[.*\])", text, flags=re.S)
    return match.group(1) if match else None

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

# ------------------------
# Tools (web_search, calculator)
# ------------------------

from ddgs import DDGS

def chat_loop():
    print("🤖 Agent ready! Type 'exit' to quit.\n")
    while True:
        user_input = input("You: ")
        if user_input.strip().lower() in ["exit", "quit", "q"]:
            print("👋 Goodbye!")
            break

        result = run_agent_once(user_input)
        
        # ✅ CHANGE: Added the block to print the log
        print("\n--- 🕵️ Agent's Thought Process ---")
        log = result.get("log", [])
        for step in log:
            print(f"➡️ {step}")
        print("---------------------------------")
        
        print("\nAgent:\n", result.get("final", "[No final output]"))

        recalls = mem_recall(user_input, k=2)
        if recalls:
            print("\n💾 Memory recall:\n", "\n".join(recalls))

# === Run chat ===
if __name__ == "__main__":
    chat_loop()


# The text of your story
knowledge_base_text = """
"Moonlit Night"

The stars shine bright in the midnight sky
A gentle breeze whispers by
The world is hushed, in quiet sleep
As the moon's soft light begins to creep

The shadows dance upon the wall
A midnight serenade, for one and all
The moon's sweet beams, illuminate the night
A peaceful scene, a wondrous sight.
"""

# The Fix: Use a relative path to save the file in /kaggle/working/
file_path = "Moonlit.txt"
with open(file_path, "w") as f:
    f.write(knowledge_base_text)

print(f"✅ '{file_path}' created successfully in /kaggle/working/.")


import gradio as gr
import markdown

# Function to handle file ingestion
import os
import traceback

def upload_file(files):
    # This function will now receive a list of files
    if not files:
        return "⚠️ Please upload at least one file."

    results = []
    # Loop through each file in the list
    for file in files:
        file_path = file.name
        try:
            # Call the ingestion function for each file
            status = ingest_knowledge_base(file_path)
            results.append(status)
        except Exception as e:
            error_msg = "".join(traceback.format_exception_only(type(e), e))
            print("❌ Ingestion failed:", error_msg)
            results.append(f"❌ Error ingesting {os.path.basename(file_path)}: {error_msg}")
    
    # Return a single string with the status of all files
    return "\n".join(results)



# Function for chat