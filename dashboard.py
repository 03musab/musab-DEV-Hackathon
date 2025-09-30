# dashboard.py
# This file contains the core agent graph logic.
from __future__ import annotations
import os, re, json, ast
from typing import TypedDict, List, Dict, Any, Optional

import dotenv
from langchain_cerebras import ChatCerebras
from langchain.schema import HumanMessage, SystemMessage, AIMessage
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langgraph.graph import StateGraph, END
from ddgs import DDGS
from langchain_community.document_loaders import (
    TextLoader, PyPDFLoader, CSVLoader, UnstructuredExcelLoader,
    UnstructuredPowerPointLoader, UnstructuredWordDocumentLoader
)

# Import helper functions and all prompts from their separate files
from memory import mem_add, mem_recall
from utils import tool_web_search, tool_calculator, tool_write_file, tool_read_file, tool_run_code
from config import safe_json_loads
from prompts import (
    DIRECT_ANSWER_SYS, INTENT_DISTILLER_PROMPT,
    PLANNER_SYS, EXECUTOR_SYS, VERIFIER_SYS
)
# New: Import the TOOLS dictionary from the tools.py file
from tools import TOOLS
from coding import tool_coding_agent

dotenv.load_dotenv()
print("API key loaded ✅")

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
# The TOOLS dictionary and tool functions have been moved to tools.py

class GraphState(TypedDict, total=False):
    user_input: str
    memory_context: str
    plan: List[Dict[str, Any]]
    observations: List[Dict[str, Any]]
    draft: str
    feedback: str
    reflections: int
    final: str
    log: List[str]
    history: List[Dict[str, Any]]

def node_direct_answer(state: GraphState) -> GraphState:
    log = state.get("log", [])
    mem_list = mem_recall(state.get("user_input", ""), k=5)
    facts = mem_recall("fact:", k=5)
    mem_list.extend(facts)
    mem_list = list(set(mem_list))
    if not mem_list:
        log.append("🤔 Direct Answer: No relevant memory found. Proceeding to planner.")
        return {"log": log}
    mem_text = "\n".join(mem_list) if mem_list else "<none>"
    prompt = (DIRECT_ANSWER_SYS + "\nRelevant memory:\n" + mem_text + "\nUser input:\n" + state.get("user_input", ""))
    response = _llm.invoke(prompt).content.strip()
    if "NO_DIRECT_ANSWER" in response:
        log.append("🤔 Direct Answer: No direct answer found in memory. Proceeding to planner.")
        return {"log": log}
    else:
        log.append("✅ Direct Answer: Found a direct answer in memory. Finalizing.")
        return {"final": response, "log": log}





def node_planner(state: GraphState) -> GraphState:
    log = state.get("log", [])
    user_input = state.get("user_input", "")
    file_path = state.get("file_path")
    history = state.get("history", [])
    
    # Corrected: Only keep the last 5 turns of the conversation
    recent_history = history[-5:]
    
    # Format the history into a string for the prompt
    history_str = ""
    for user_msg, agent_msg in recent_history:
        history_str += f"User: {user_msg}\nAgent: {agent_msg}\n"
    
    if file_path:
        log.append(f"📝 Planner: File '{os.path.basename(file_path)}' detected. Forcing RAG search.")
        plan = [{"id": 1, "thought": "The user uploaded a file, so the answer should be in the knowledge base. I will use rag_search to find information about the user's query.", "tool": "rag_search", "args": {"query": user_input}, "output_key": "rag_results"}]
        return {"plan": plan, "log": log, "file_path": file_path, "history": history}
    
    mem_list = mem_recall(user_input, k=4)
    mem_text = "\n".join(mem_list) if mem_list else "<none>"
    file_info = f"\nFile Path: \"{file_path}\"" if file_path else "\nFile Path: null"
    
    # Update the prompt to include the history
    distiller_prompt = (
        INTENT_DISTILLER_PROMPT
        + "\nChat History:\n" + history_str
        + "\nRelevant memory:\n" + mem_text
        + "\nUser input:\n" + user_input
        + file_info
    )
    distilled_task = _llm.invoke(distiller_prompt).content.strip()
    log.append(f"🎯 Planner: Distilled user intent to: '{distilled_task}'")
    tool_list_str = "\n".join([f"- {name}: {meta['desc']}" for name, meta in TOOLS.items()])
    planner_prompt_template = PLANNER_SYS.replace("{tool_list}", tool_list_str)
    prompt = (
        planner_prompt_template
        + "\nRelevant memory (may be empty):\n" + mem_text
        + "\nUser task:\n" + distilled_task
        + "\nRespond with ONLY JSON in the format: {\"steps\":[...] }\n"
    )
    raw = _llm.invoke(prompt).content.strip()
    parsed = safe_json_loads(raw)
    steps = parsed.get("steps") if isinstance(parsed, dict) and isinstance(parsed.get("steps"), list) else []
    log.append(f"📝 Planner: Generated a plan with {len(steps)} step(s).")
    
    return {"plan": steps, "log": log, "history": history}

def node_executor(state: GraphState) -> GraphState:
    """Runs tools and generates a draft answer."""
    log = state.get("log", [])
    plan = state.get("plan", [])
    
    print(f"DEBUG: Executor received plan: {plan}")

    tool_steps = [step for step in plan if step.get("tool")]
    if tool_steps:
        tools_str = ", ".join([step['tool'] for step in tool_steps])
        log.append(f"🛠️ Executor: Running tool(s): {tools_str}")
    else:
        log.append("🧠 Executor: No tools to run. Answering from general knowledge.")

    observations = []
    for step in plan:
        tool_name = step.get("tool")
        args = step.get("args", {}) or {}
        if tool_name and tool_name in TOOLS:
            try:
                obs = TOOLS[tool_name]["func"](args)
            except Exception as e:
                obs = {"error": f"tool_error: {e}"}
        else:
            obs = {"note": "no_tool"}
        observations.append({"id": step.get("id"), "tool": tool_name, "args": args, "observation": obs})

    print(f"DEBUG: Executor received observations: {observations}")

    context_blob = json.dumps({"plan": plan, "observations": observations, "user_input": state.get("user_input", "")}, ensure_ascii=False)
    draft_prompt = "You are the Executor... \nContext JSON:\n" + context_blob + "\nDraft the answer now."
    draft = _llm.invoke(draft_prompt).content.strip()
    
    return {"observations": observations, "draft": draft, "log": log}


def node_verifier(state: GraphState) -> GraphState:
    log = state.get("log", [])
    prompt = (VERIFIER_SYS + "\nUser input:\n" + state.get("user_input", "") + "\nDraft:\n" + (state.get("draft", "") or "") + "\nObservations (for verification):\n" + json.dumps(state.get("observations", []), ensure_ascii=False))
    raw = _llm.invoke(prompt).content.strip()
    parsed = safe_json_loads(raw)
    if isinstance(parsed, dict) and parsed.get("approved") and parsed.get("final"):
        log.append("✅ Verifier: Draft approved.")
        return {"final": parsed.get("final"), "log": log}
    fb = parsed.get("feedback", "") if isinstance(parsed, dict) else "needs another pass"
    log.append(f"❌ Verifier: Draft not approved. Feedback: '{fb[:50]}...'. Replanning.")
    mem_add(f"verifier_feedback: {fb}", kind="feedback")
    return {"feedback": fb, "reflections": (state.get("reflections", 0) + 1), "log": log}

def node_memory_update(state: GraphState) -> GraphState:
    log = state.get("log", [])
    log.append("💾 Memory: Saving final answer and user query to long-term memory.")
    ui = state.get("user_input", "")
    final = state.get("final", "")
    if ui: mem_add(ui, kind="user")
    if final: mem_add(final, kind="agent")
    low = ui.lower()
    if "my name is" in low:
        name = low.split("my name is", 1)[-1].strip().strip(".?! ")
        if name:
            fact_json = json.dumps({"entity": "user", "attribute": "name", "value": name})
            mem_add(fact_json, kind="fact")
    if "your name is" in low or "ur name is" in low:
        name = low.split(" is ", 1)[-1].strip().strip(".?! ")
        if name:
            fact_json = json.dumps({"entity": "agent", "attribute": "name", "value": name})
            mem_add(fact_json, kind="fact")
    if "my brother name is" in low:
        name = low.split("my brother name is", 1)[-1].strip().strip(".?! ")
        if name:
            fact_json = json.dumps({"entity": "user's brother", "attribute": "name", "value": name})
            mem_add(fact_json, kind="fact")
    return {"log": log}

def finalizer(state: GraphState) -> GraphState:
    final_answer = state.get("draft") or "[Agent had no result]"
    return {**state, "final": final_answer}

def _should_reflect(state: GraphState) -> str:
    if state.get("final"):
        return "approved"
    if int(state.get("reflections", 0)) >= MAX_REFLECTIONS:
        return "give_up"
    return "replan"

def should_plan_or_finish(state: GraphState) -> str:
    if state.get("final"):
        return "finish"
    else:
        return "plan"
        
def build_graph():
    workflow = StateGraph(GraphState)
    workflow.add_node("direct_answer", node_direct_answer)
    workflow.add_node("planner", node_planner)
    workflow.add_node("executor", node_executor)
    workflow.add_node("verifier", node_verifier)
    workflow.add_node("finalizer", finalizer)
    workflow.add_node("memory", node_memory_update)
    workflow.set_entry_point("direct_answer")
    workflow.add_conditional_edges(
        "direct_answer",
        should_plan_or_finish,
        {
            "finish": "memory",
            "plan": "planner"
        }
    )
    workflow.add_edge("planner", "executor")
    workflow.add_edge("executor", "verifier")
    workflow.add_conditional_edges(
        "verifier",
        _should_reflect,
        {
            "replan": "planner",
            "approved": "memory",
            "give_up": "finalizer"
        }
    )
    workflow.add_edge("finalizer", "memory")
    workflow.add_edge("memory", END)
    return workflow.compile()

def run_agent_once(user_input: str, history: List[Dict[str, Any]]) -> Dict[str, Any]:
    global _vectorstore
    
    graph = build_graph()
    state: GraphState = {
        "user_input": user_input, 
        "reflections": 0, 
        "log": [],
        "history": history # <-- New: Add history to the state
    }
    result = graph.invoke(state)
    return result

def _run_tools(steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    observations: List[Dict[str, Any]] = []
    for step in steps:
        tool_name = step.get("tool")
        args = step.get("args", {}) or {}
        if tool_name and tool_name in TOOLS:
            try:
                obs = TOOLS[tool_name]["func"](args)
            except Exception as e:
                obs = {"error": f"tool_error: {e}"}
        else:
            obs = {"note": "no_tool"}
        observations.append({
            "id": step.get("id"),
            "tool": tool_name,
            "args": args,
            "observation": obs,
        })
    return observations


if __name__ == "__main__":
    _vectorstore = Chroma(
        collection_name=MEM_COLLECTION,
        embedding_function=_embedding_fn,
        persist_directory=PERSIST_DIR
    )
    
    if not os.environ.get("API_KEY"):
        print("[WARN] API_KEY is not set. Set it before running for LLM calls.")
    demo_q = "Give me 3 bullet points on why AI agents are useful for students."
    # Pass an empty list for the history argument
    out = run_agent_once(demo_q, [])
    print("\n=== FINAL ANSWER ===\n", out.get("final"))
    print("\n--- Debug state keys ---\n", list(out.keys()))