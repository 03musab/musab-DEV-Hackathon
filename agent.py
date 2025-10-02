# agent.py
from __future__ import annotations
import os
import json
from typing import TypedDict, List, Dict, Any, Optional

from langchain_chroma import Chroma
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langgraph.graph import StateGraph, END
from langchain_community.document_loaders import (
    TextLoader, PyPDFLoader, CSVLoader, UnstructuredExcelLoader,
    UnstructuredPowerPointLoader, UnstructuredWordDocumentLoader
)

from core.config import (
    _llm, _embedding_fn, RAG_PERSIST_DIR, RAG_COLLECTION,
    MAX_REFLECTIONS
)
from core.utils import safe_json_loads
from core.memory import mem_add, mem_recall
from tools import TOOLS

# --- Prompts (formerly prompts.py) ---

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
- If the user's input contains keywords like "document," "file," "uploaded," "ingested," or "saved," the distilled task MUST include a step to use the `rag_search` tool.
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
You are the Planner, a specialized agent within a multi-agent system that includes other agents like a 'Research Agent' and a 'Critic Agent'. Your primary role is to create a step-by-step plan to answer the user's task.

**VERY IMPORTANT**: Before creating a new plan, you must check the 'Relevant memory'.
- If the memory contains a satisfactory answer, your plan should be a single step to state the answer directly without using any tools.
- This check is crucial for efficiency and to avoid redundant work by other agents in the system.

**CRITICAL RULE: If the user's request is about a document, a file, or asks to 'summarize this', you MUST use the `rag_search` tool.**

Available tools:
{tool_list}

**CRITICAL RULES: for coding_agent**
1.  If the user asks you to write, execute, debug, test, or analyze code, or if the request contains keywords like "function," "class," "script," "bug," or "run this command," you MUST use the `coding_agent_tool`.
2.  The `user_input` argument for `coding_agent_tool` should be a detailed description of the coding task.


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
      "thought": "The user wants a summary of a document. No specific file was selected, so I will search the entire knowledge base.",
      "tool": "rag_search",
      "args": {
        "query": "summarize the document"
      },
      "output_key": "poem_content"
    }
  ]
}

**Example 2 (Specific File Query):**
User Task: "summarize the main points of JobSnap_PRO_PLAN_FEATURES.docx"
Correct Plan:
{
  "steps": [
    {
      "id": 1,
      "thought": "The user wants a summary of a specific file. I must use the rag_search tool and provide the filename in the `source_file` argument.",
      "tool": "rag_search",
      "args": {
        "query": "summarize the main points",
        "source_file": "JobSnap_PRO_PLAN_FEATURES.docx"
      },
      "output_key": "summary_content"
    }
  ]
}

Return a STRICT JSON array named 'steps'.
"""
EXECUTOR_SYS = """
You are the Executor. Given the user's request, the plan, and tool observations,
Write a concise, factual draft answer.
- If observations include search results, integrate them directly into the answer. Do not cite them or fabricate links.
- If a tool indicates "No relevant info found", state that directly and concisely. Do not elaborate or ask for more information.
- If no tools were used, answer from general knowledge + memory context.
- Provide ONLY the direct answer to the user's question. Do not include any conversational filler, intros, outros, or explanations of your process.
"""
VERIFIER_SYS = """
You are the Verifier. Your job is to check the draft for factuality, clarity, and task completion.
- If the draft is a greeting, a simple conversational response, or an acknowledgement, it is considered approved and complete.
- If the draft is a factual answer, check it against the provided observations for accuracy.
Return ONLY JSON: {"approved": bool, "feedback": "...", "final": "..."}
- If approved: Polish the draft to be a direct, non-conversational final answer, removing any conversational filler, and place it in 'final'.
- If NOT approved: Explain issues in 'feedback' and leave 'final' empty.
Be conservative; prefer one more revision if unsure.
"""

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

# --- Agent State and Nodes ---

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
        # Return the original state, plus the updated log
        return {**state, "log": log}
    else:
        log.append("✅ Direct Answer: Found a direct answer in memory. Finalizing.")
        # Return the original state, plus the final answer and updated log
        return {**state, "final": response, "log": log}


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
    # If there's a single observation and it's a string, we can likely use it directly.
    # This is a good heuristic for when a sub-agent returns a complete answer.
    if len(observations) == 1 and isinstance(observations[0].get("observation"), str):
        draft = observations[0]["observation"]
        log.append("📝 Executor: Using direct string output from tool as draft.")
        return {"observations": observations, "draft": draft, "log": log}

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
        
# --- Graph Builder ---

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

# --- Main Agent Runner ---

def run_agent_once(user_input: str, history: List[Dict[str, Any]]) -> Dict[str, Any]:
    graph = build_graph()
    state: GraphState = {
        "user_input": user_input, 
        "reflections": 0, 
        "log": [],
        "history": history # <-- New: Add history to the state
    }
    result = graph.invoke(state)
    return result