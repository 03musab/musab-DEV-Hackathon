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

# Only import helper functions that DO NOT import back from this file
from config import safe_json_loads
from memory import mem_add, mem_recall
from prompts import (
    DIRECT_ANSWER_SYS, PLANNER_SYS, EXECUTOR_SYS, VERIFIER_SYS
)
from tools import TOOLS
from globals import (
    _llm, _embedding_fn, _vectorstore, MAX_REFLECTIONS, MEM_COLLECTION,
    PERSIST_DIR, RAG_PERSIST_DIR, RAG_COLLECTION
)

# Load API key from .env file
dotenv.load_dotenv()
print("API key loaded ✅")

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

class GraphState(TypedDict, total=False):
    user_input: str
    memory_context: str
    plan: List[Dict[str, Any]]
    observations: List[Dict[str, Any]]
    draft: str
    feedback: str
    reflections: int
    final: str
    file_path: Optional[str]
    log: List[str]

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

    mem_list = mem_recall(user_input, k=4)
    mem_text = "\n".join(mem_list) if mem_list else "<none>"
    log.append(f"🎯 Planner: Using user input directly for planning: '{user_input}'")
    tool_list_str = "\n".join([f"- {name}: {meta['desc']}" for name, meta in TOOLS.items()])
    planner_prompt_template = PLANNER_SYS.replace("{tool_list}", tool_list_str)
    prompt = (
        planner_prompt_template + "\nRelevant memory (may be empty):\n" + mem_text + "\nUser task:\n" + user_input + "\nRespond with ONLY JSON in the format: {\"steps\":[...] }\n"
    )
    raw = _llm.invoke(prompt).content.strip()
    parsed = safe_json_loads(raw)
    steps = parsed.get("steps") if isinstance(parsed, dict) and isinstance(parsed.get("steps"), list) else []
    log.append(f"📝 Planner: Generated a plan with {len(steps)} step(s).")
    return {"plan": steps, "log": log}

def node_executor(state: GraphState) -> GraphState:
    """Runs tools and generates a draft answer."""
    log = state.get("log", [])
    plan = state.get("plan", [])
    
    # --- Start of Debugging Code ---
    print(f"DEBUG: Executor received plan: {plan}")
    # --- End of Debugging Code ---

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

    # --- Start of Debugging Code ---
    print(f"DEBUG: Executor received observations: {observations}")
    # --- End of Debugging Code ---

    # Construct a proper prompt using the EXECUTOR_SYS system prompt
    context_for_draft = (
        f"User Request: {state.get('user_input', '')}\n"
        f"Plan: {json.dumps(plan, ensure_ascii=False)}\n"
        f"Observations: {json.dumps(observations, ensure_ascii=False)}"
    )
    draft_prompt = f"{EXECUTOR_SYS}\n\n{context_for_draft}\n\nNow, write the draft answer."
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

def run_agent_once(user_input: str, file_path: Optional[str] = None) -> Dict[str, Any]:
    # Correctly initialize the vectorstore and assign it to the global variable
    # that the rest of the application (e.g., memory.py) uses.
    globals()["_vectorstore"] = Chroma(
        collection_name=MEM_COLLECTION,
        embedding_function=_embedding_fn,
        persist_directory=PERSIST_DIR
    )
    graph = build_graph()
    state: GraphState = {"user_input": user_input, "file_path": file_path, "reflections": 0, "log": []}
    result = graph.invoke(state, {"recursion_limit": 150})
    return result

if __name__ == "__main__":
    if not os.environ.get("API_KEY"):
        print("[WARN] API_KEY is not set. Set it before running for LLM calls.")
    demo_q = "Give me 3 bullet points on why AI agents are useful for students."
    out = run_agent_once(demo_q, file_path=None)
    print("\n=== FINAL ANSWER ===\n", out.get("final"))
    print("\n--- Debug state keys ---\n", list(out.keys()))