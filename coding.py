# coding.py
from __future__ import annotations
import os, json
from typing import TypedDict, List, Dict, Any, Optional
from langchain.schema import HumanMessage, SystemMessage, AIMessage
from langgraph.graph import StateGraph, END

# This is a custom ToolExecutor to bypass the import error.
class ToolInvocation:
    def __init__(self, tool, tool_input):
        self.tool = tool
        self.tool_input = tool_input

class ToolExecutor:
    def __init__(self, tools):
        self.tools = {tool.__name__: tool for tool in tools}

    def invoke(self, tool_invocation: ToolInvocation):
        tool_function = self.tools.get(tool_invocation.tool)
        if not tool_function:
            return {"error": f"Tool '{tool_invocation.tool}' not found."}
        return tool_function(**tool_invocation.tool_input)

from globals import _llm, MAX_REFLECTIONS
from utils import tool_write_file, tool_read_file, tool_run_code
from prompts import CODE_PLANNER_SYS

class CodingAgentState(TypedDict):
    user_input: str
    plan: List[str]
    current_code: str
    log: List[str]

CODING_TOOLS = [tool_write_file, tool_read_file, tool_run_code]
coding_tool_executor = ToolExecutor(CODING_TOOLS)

def node_coding_planner(state: CodingAgentState) -> CodingAgentState:
    print("📝 Coding Planner: Planning the task.")
    tool_list_str = "\n".join([f"- {tool.__name__}: {tool.__doc__}" for tool in CODING_TOOLS])
    prompt = CODE_PLANNER_SYS.replace("{tool_list}", tool_list_str)
    
    raw = _llm.invoke(prompt + f"\nUser input:\n{state.get('user_input', '')}").content.strip()
    
    try:
        plan = json.loads(raw)
    except json.JSONDecodeError:
        print(f"❌ Planner failed to parse JSON: {raw}")
        plan = [{"tool": "respond", "args": {"message": "I was unable to create a plan."}}]
    
    return {"plan": plan, "log": [f"📝 Plan generated: {plan}"]}

def node_coding_executor(state: CodingAgentState) -> CodingAgentState:
    print("🛠️ Coding Executor: Executing the plan.")
    plan = state.get("plan", [])
    
    observations = []
    for step in plan:
        tool_invocation = ToolInvocation(tool=step["tool"], tool_input=step["args"])
        try:
            obs = coding_tool_executor.invoke(tool_invocation)
        except Exception as e:
            obs = {"error": f"Tool execution failed: {str(e)}"}
        observations.append(obs)
    
    draft_prompt = f"Based on the following observations: {observations}\nDraft the final response."
    draft = _llm.invoke(draft_prompt).content.strip()
    
    return {"observations": observations, "draft": draft}

def build_coding_agent_graph():
    def node_coding_verifier(state: CodingAgentState) -> CodingAgentState:
        print("✅ Coding Verifier: Approving the solution.")
        return {"final": state.get("draft", ""), "approved": True}

    workflow = StateGraph(CodingAgentState)
    
    workflow.add_node("coding_planner", node_coding_planner)
    workflow.add_node("coding_executor", node_coding_executor)
    workflow.add_node("coding_verifier", node_coding_verifier)
    
    workflow.set_entry_point("coding_planner")
    workflow.add_edge("coding_planner", "coding_executor")
    workflow.add_edge("coding_executor", "coding_verifier")
    workflow.add_edge("coding_verifier", END)
    
    return workflow.compile()

def tool_coding_agent(user_input: str) -> Dict[str, Any]:
    print("🤖 Main Agent: Invoking specialized coding agent.")
    coding_graph = build_coding_agent_graph()
    result = coding_graph.invoke({"user_input": user_input})
    return {"response": result["final"]}