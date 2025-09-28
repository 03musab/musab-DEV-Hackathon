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
from utils import tool_web_search, tool_calculator
from config import safe_json_loads

# Load API key from .env file
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

DIRECT_ANSWER_SYS = """
You are a helpful assistant that answers questions ONLY from the provided memory context.
The memory may contain structured facts in JSON format, like {"entity": "user", "attribute": "name", "value": "haad"}.

- To answer the user's question, you MUST parse these JSON facts.
- When asked 'what is my name' or about the 'user', look for facts where 'entity' is 'user'.
- When asked 'what is your name' or about the 'agent', look for facts where 'entity' is 'agent'.
- Use this information to answer precisely. Do not mention the JSON structure in your answer.

- If the memory does NOT contain enough information to answer, you MUST respond with the exact phrase: 'NO_DIRECT_ANSWER' and nothing else.
"""
INTENT_DISTILLER_PROMPT = """
You are an intent distiller. Your job is to analyze the conversation and determine the user's real, actionable task.
- If the user has provided a file, the primary task is to process that file using the instructions in the user's text.
- If the user refers to a specific file (e.g., "in summary.txt"), separate the core question from the file reference.

Your output should be a clear, actionable instruction for the Planner AI.

Example 1:
User input: "summarize the main points of the attached file"
File Path: "/path/to/doc.txt"
Result: "The user has uploaded a file at /path/to/doc.txt and wants a summary. The first step is to add the file to the knowledge base, then search it for the main points."

Example 2:
User input: "whats the poem name in summary.txt"
File Path: null
Result: "The user wants to know the name of the poem inside the file 'summary.txt'. The task is to search within that specific file for the poem's title."

Now, distill the intent from the following:
"""
PLANNER_SYS = """
You are the Planner. Your goal is to create a step-by-step plan to answer the user's task.
**VERY IMPORTANT: Before creating a new plan, check 'Relevant memory'. If the answer is already there, your plan should be a single step to state the answer directly without using tools.**

Available tools:
{tool_list}

**CRITICAL RULES for rag_search:**
1.  When the user asks about a specific file (e.g., "in summary.txt"), you MUST use the `rag_search` tool with the `source_file` argument set to the filename (e.g., "summary.txt").
2.  When using `source_file`, the `query` argument MUST be a question that represents the user's core goal. **DO NOT leave the query empty.** Reformulate the user's request into a proper question for the search.

**Example of a good plan:**
User Task: "The user wants to know the name of the poem inside the file 'summary.txt'."
Correct Plan:
{
  "steps": [
    {
      "id": 1,
      "thought": "I need to find the name of the poem inside 'summary.txt'. I will use rag_search and filter by the source file. I will also formulate a query to find the poem's name.",
      "tool": "rag_search",
      "args": {
        "query": "What is the name of the poem?",
        "source_file": "summary.txt"
      },
      "output_key": "poem_content"
    }
  ]
}

Return a STRICT JSON array named 'steps'.
"""
EXECUTOR_SYS = """
You are the Executor. Given the user's request, the plan, and tool observations,
write a clear, helpful draft answer. If observations include search results, cite them inline textually (titles/domains), but do not fabricate links.
If no tools were used, answer from general knowledge + memory context. Keep it concise unless the user asked for depth.
- Do not add any introductory phrases like "Based on the search results..." or "The resume states...".
- Provide only the direct answer to the user's question.
"""
VERIFIER_SYS = """
You are the Verifier. Check the draft for factuality, clarity, safety, and task completion.
Return ONLY JSON: {"approved": bool, "feedback": "...", "final": "..."}
- If approved: polish the draft lightly and place in 'final'.
- If NOT approved: explain issues in 'feedback' and leave 'final' empty.
Be conservative; prefer one more revision if unsure.
"""

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
    
    # File: dashboard.py

def node_planner(state: GraphState) -> GraphState:
    log = state.get("log", [])
    user_input = state.get("user_input", "")
    file_path = state.get("file_path")

    
    if file_path:
        log.append(f"📝 Planner: File '{os.path.basename(file_path)}' detected. Forcing RAG search.")
        plan = [{"id": 1, "thought": "The user uploaded a file, so the answer should be in the knowledge base. I will use rag_search to find information about the user's query.", "tool": "rag_search", "args": {"query": user_input}, "output_key": "rag_results"}]
        return {"plan": plan, "log": log, "file_path": file_path}
    
    mem_list = mem_recall(user_input, k=4)
    mem_text = "\n".join(mem_list) if mem_list else "<none>"
    file_info = f"\nFile Path: \"{file_path}\"" if file_path else "\nFile Path: null"
    distiller_prompt = (
        INTENT_DISTILLER_PROMPT + "\nRelevant memory:\n" + mem_text + "\nUser input:\n" + user_input + file_info
    )
    distilled_task = _llm.invoke(distiller_prompt).content.strip()
    log.append(f"🎯 Planner: Distilled user intent to: '{distilled_task}'")
    tool_list_str = "\n".join([f"- {name}: {meta['desc']}" for name, meta in TOOLS.items()])
    planner_prompt_template = PLANNER_SYS.replace("{tool_list}", tool_list_str)
    prompt = (
        planner_prompt_template + "\nRelevant memory (may be empty):\n" + mem_text + "\nUser task:\n" + distilled_task + "\nRespond with ONLY JSON in the format: {\"steps\":[...] }\n"
    )
    raw = _llm.invoke(prompt).content.strip()
    parsed = safe_json_loads(raw)
    steps = parsed.get("steps") if isinstance(parsed, dict) and isinstance(parsed.get("steps"), list) else []
    log.append(f"📝 Planner: Generated a plan with {len(steps)} step(s).")
    return {"plan": steps, "log": log}

# File: dashboard.py

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

def run_agent_once(user_input: str) -> Dict[str, Any]:
    global _vectorstore
    _vectorstore = Chroma(
        collection_name=MEM_COLLECTION,
        embedding_function=_embedding_fn,
        persist_directory=PERSIST_DIR
    )
    graph = build_graph()
    state: GraphState = {"user_input": user_input, "reflections": 0, "log": []}
    result = graph.invoke(state)
    return result

if __name__ == "__main__":
    if not os.environ.get("API_KEY"):
        print("[WARN] API_KEY is not set. Set it before running for LLM calls.")
    demo_q = "Give me 3 bullet points on why AI agents are useful for students."
    out = run_agent_once(demo_q)
    print("\n=== FINAL ANSWER ===\n", out.get("final"))
    print("\n--- Debug state keys ---\n", list(out.keys()))