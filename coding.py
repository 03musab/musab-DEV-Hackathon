from __future__ import annotations
import os, json
from typing import TypedDict, List, Dict, Any, Optional
from langchain.schema import HumanMessage, SystemMessage, AIMessage
from langgraph.graph import StateGraph, END
from langchain_cerebras import ChatCerebras

# ==================== Custom Tool Executor ====================
class ToolInvocation:
    """Represents a tool invocation with tool name and input parameters."""
    def __init__(self, tool, tool_input):
        self.tool = tool
        self.tool_input = tool_input

class ToolExecutor:
    """Executes tools based on their name and input parameters."""
    def __init__(self, tools):
        self.tools = {tool.__name__: tool for tool in tools}

    def invoke(self, tool_invocation: ToolInvocation):
        tool_function = self.tools.get(tool_invocation.tool)
        if not tool_function:
            return {"error": f"❌ Tool '{tool_invocation.tool}' not found."}
        return tool_function(**tool_invocation.tool_input)

# ==================== LLM Configuration ====================
from core.config import _llm, LLM_MODEL

# Specialized LLM optimized for coding tasks
_coding_llm = ChatCerebras(
    model="qwen-3-coder-480b",
    temperature=0.7,
    api_key=os.getenv("API_KEY"),
    max_tokens=4000,
    top_p=0.8
)

from tools import tool_write_file, tool_read_file, tool_run_code
from prompts import CODE_PLANNER_SYS

# ==================== State Definition ====================
class CodingAgentState(TypedDict):
    """State container for the coding agent workflow."""
    user_input: str
    plan: List[Dict[str, Any]]
    observations: List[Dict[str, Any]]
    draft: str
    final: str
    approved: bool
    log: List[str]

# ==================== Tool Configuration ====================
CODING_TOOLS = [tool_write_file, tool_read_file, tool_run_code]
coding_tool_executor = ToolExecutor(CODING_TOOLS)

# ==================== UI Helper Functions ====================
def format_section_header(title: str, emoji: str = "📌") -> str:
    """Create a visually distinct section header."""
    border = "─" * 50
    return f"\n{border}\n{emoji} {title}\n{border}"

def format_code_block(code: str, language: str = "python") -> str:
    """Ensure code is properly formatted in markdown code blocks."""
    if not code.strip().startswith("```"):
        return f"```{language}\n{code}\n```"
    return code

def format_step_result(step_num: int, total: int, tool_name: str, success: bool) -> str:
    """Format execution step results for better readability."""
    icon = "✅" if success else "❌"
    progress = f"[{step_num}/{total}]"
    return f"{icon} {progress} {tool_name}"

def format_error_message(error: str) -> str:
    """Format error messages in a user-friendly way."""
    return f"⚠️  **Error:** {error}"

def get_language_from_filename(filename: str) -> str:
    """
    Detect the programming language from a filename extension.
    
    Args:
        filename: The name of the file
        
    Returns:
        Language identifier for syntax highlighting
    """
    extension_map = {
        '.py': 'python',
        '.js': 'javascript',
        '.jsx': 'jsx',
        '.ts': 'typescript',
        '.tsx': 'tsx',
        '.java': 'java',
        '.cpp': 'cpp',
        '.c': 'c',
        '.cs': 'csharp',
        '.go': 'go',
        '.rs': 'rust',
        '.rb': 'ruby',
        '.php': 'php',
        '.swift': 'swift',
        '.kt': 'kotlin',
        '.scala': 'scala',
        '.sh': 'bash',
        '.bash': 'bash',
        '.zsh': 'zsh',
        '.html': 'html',
        '.css': 'css',
        '.scss': 'scss',
        '.sass': 'sass',
        '.json': 'json',
        '.xml': 'xml',
        '.yaml': 'yaml',
        '.yml': 'yaml',
        '.md': 'markdown',
        '.sql': 'sql',
        '.r': 'r',
        '.m': 'matlab',
        '.dart': 'dart',
        '.lua': 'lua',
        '.pl': 'perl',
        '.vim': 'vim',
    }
    
    # Extract extension from filename
    if '.' in filename:
        ext = '.' + filename.rsplit('.', 1)[-1].lower()
        return extension_map.get(ext, 'text')
    
    return 'text'

def format_code_properly(code: str, language: str = 'python') -> str:
    """
    Format code with proper indentation and structure.
    
    Args:
        code: The code to format
        language: The programming language
        
    Returns:
        Properly formatted code string
    """
    # Remove leading/trailing whitespace
    code = code.strip()
    
    # Language-specific formatting
    if language == 'python':
        try:
            import ast
            # Try to parse and verify it's valid Python
            ast.parse(code)
            
            # Fix common indentation issues
            lines = code.split('\n')
            formatted_lines = []
            indent_level = 0
            
            for line in lines:
                stripped = line.lstrip()
                
                # Skip empty lines
                if not stripped:
                    formatted_lines.append('')
                    continue
                
                # Decrease indent for closing brackets, 'elif', 'else', 'except', 'finally'
                if stripped.startswith((')', ']', '}', 'elif ', 'else:', 'except', 'finally')):
                    indent_level = max(0, indent_level - 1)
                
                # Add the line with proper indentation
                formatted_lines.append('    ' * indent_level + stripped)
                
                # Increase indent after colons (def, class, if, for, while, etc.)
                if stripped.rstrip().endswith(':'):
                    indent_level += 1
                
                # Decrease indent for single-line after pass/return/break/continue
                if stripped in ('pass', 'break', 'continue') or stripped.startswith('return '):
                    indent_level = max(0, indent_level - 1)
            
            return '\n'.join(formatted_lines)
            
        except (SyntaxError, ImportError):
            # If parsing fails or ast not available, return original
            pass
    
    elif language == 'json':
        try:
            # Format JSON with proper indentation
            parsed = json.loads(code)
            return json.dumps(parsed, indent=2, ensure_ascii=False)
        except (json.JSONDecodeError, ValueError):
            pass
    
    # For other languages or if formatting fails, normalize indentation
    lines = code.split('\n')
    
    # Find the minimum indentation (excluding empty lines)
    min_indent = float('inf')
    for line in lines:
        if line.strip():  # Skip empty lines
            indent = len(line) - len(line.lstrip())
            min_indent = min(min_indent, indent)
    
    # Remove excess indentation
    if min_indent < float('inf') and min_indent > 0:
        normalized_lines = []
        for line in lines:
            if line.strip():
                normalized_lines.append(line[min_indent:])
            else:
                normalized_lines.append('')
        return '\n'.join(normalized_lines)
    
    return code

# ==================== Agent Nodes ====================
def node_coding_planner(state: CodingAgentState) -> CodingAgentState:
    """
    📝 Planning Phase: Analyze the task and create an execution plan.
    Breaks down coding tasks into actionable steps with appropriate tools.
    """
    print("\n" + "="*60)
    print("📝 PLANNING PHASE: Analyzing your request...")
    print("="*60)
    
    tool_descriptions = "\n".join([
        f"  • {tool.__name__}: {tool.__doc__}" 
        for tool in CODING_TOOLS
    ])
    
    planning_prompt = f"""{CODE_PLANNER_SYS}

🛠️  Available Tools:
{tool_descriptions}

💬 User Request:
{state.get('user_input', '')}

📋 Task:
Generate a detailed JSON execution plan. Each step must include:
- "tool": exact tool name to use
- "args": dictionary of arguments (be specific with filenames, content, etc.)
- "reason": clear explanation of why this step is necessary

📝 Output Format (JSON only, no additional text):
[
  {{
    "tool": "tool_write_file",
    "args": {{"file_path": "example.py", "text": "# Your code here"}},
    "reason": "Create a Python script with the required functionality"
  }},
  {{
    "tool": "tool_run_code",
    "args": {{"filename": "example.py"}},
    "reason": "Execute and verify the code works correctly"
  }}
]

⚠️  Important: Return ONLY the JSON array."""

    try:
        print("⏳ Generating execution plan...")
        raw_response = _coding_llm.invoke(planning_prompt).content.strip()
        
        # Extract JSON from markdown code blocks if present
        if "```json" in raw_response:
            raw_response = raw_response.split("```json")[1].split("```")[0].strip()
        elif "```" in raw_response:
            raw_response = raw_response.split("```")[1].split("```")[0].strip()
        
        plan = json.loads(raw_response)
        
        if not isinstance(plan, list):
            raise ValueError("Plan must be a list of executable steps")
        
        # Log successful planning
        log = state.get("log", [])
        log.append(f"✅ Generated execution plan with {len(plan)} steps")
        
        print(f"✅ Plan ready: {len(plan)} steps identified\n")
        
        return {"plan": plan, "log": log}
        
    except (json.JSONDecodeError, ValueError) as e:
        error_message = f"Planning failed: {str(e)}"
        print(f"\n❌ {error_message}")
        print(f"📄 Raw output (truncated): {raw_response[:300]}...\n")
        
        return {
            "plan": [],
            "draft": format_section_header("Planning Error", "❌") + 
                    f"\n\nI encountered an issue while creating the execution plan:\n\n" +
                    format_error_message(str(e)) +
                    f"\n\n💡 **Suggestion:** Try rephrasing your request with more specific details.",
            "log": state.get("log", []) + [f"❌ Planning error: {str(e)}"]
        }

def node_coding_executor(state: CodingAgentState) -> CodingAgentState:
    """
    🛠️  Execution Phase: Execute the planned steps sequentially.
    Runs each tool and collects results for verification.
    """
    print("\n" + "="*60)
    print("🛠️  EXECUTION PHASE: Running your code tasks...")
    print("="*60 + "\n")
    
    plan = state.get("plan", [])
    
    # Handle case where planning failed
    if not plan:
        return {
            "observations": [],
            "draft": state.get("draft", format_section_header("No Execution", "⚠️") + 
                          "\n\nNo execution plan was generated. Please try again with a clearer request.")
        }
    
    observations = []
    execution_log = []
    total_steps = len(plan)
    
    # Execute each step with progress tracking
    for i, step in enumerate(plan, 1):
        tool_name = step.get("tool", "unknown")
        tool_args = step.get("args", {})
        reason = step.get("reason", "No reason provided")
        
        print(f"📍 Step {i}/{total_steps}: {tool_name}")
        print(f"   Reason: {reason}")
        
        tool_invocation = ToolInvocation(tool=tool_name, tool_input=tool_args)
        
        try:
            result = coding_tool_executor.invoke(tool_invocation)
            observations.append({
                "step": i,
                "tool": tool_name,
                "args": tool_args,
                "reason": reason,
                "result": result,
                "success": "error" not in result
            })
            print(format_step_result(i, total_steps, tool_name, True))
            execution_log.append(f"✅ Step {i}: {tool_name} completed successfully")
            
        except Exception as e:
            error_result = {"error": f"Execution failed: {str(e)}"}
            observations.append({
                "step": i,
                "tool": tool_name,
                "args": tool_args,
                "reason": reason,
                "result": error_result,
                "success": False
            })
            print(format_step_result(i, total_steps, tool_name, False))
            print(f"   Error: {str(e)}")
            execution_log.append(f"❌ Step {i}: {tool_name} failed - {str(e)}")
    
    print(f"\n✅ Execution complete: {total_steps} steps processed\n")
    
    # Generate comprehensive, user-friendly summary
    draft_prompt = f"""You are a helpful coding assistant. Create a clear, well-formatted response based on the execution results.

📌 Original Request:
{state.get('user_input', '')}

📊 Execution Results:
{json.dumps(observations, indent=2)}

📝 Your Response Should Include:

1. **Summary**: Brief overview of what was accomplished
2. **Code Created**: Show any code written (in proper markdown code blocks with syntax highlighting)
3. **Execution Output**: Display any program output or results
4. **Errors**: Clearly explain any issues encountered with potential solutions
5. **Next Steps**: Suggest what the user might want to do next (if applicable)

🎨 Formatting Requirements:
- Use markdown headers (##, ###) for sections
- ALL code MUST be in proper markdown code blocks: ```python ... ```
- Use bullet points for lists
- Use **bold** for emphasis
- Use emojis sparingly for visual appeal
- Keep explanations clear and concise

Make your response professional, friendly, and easy to understand."""

    try:
        draft = _coding_llm.invoke(draft_prompt).content.strip()
    except Exception as e:
        draft = format_section_header("Execution Summary", "📊") + f"""

**Status**: Tasks executed but summary generation failed

**Error**: {str(e)}

**Raw Observations**:
```json
{json.dumps(observations, indent=2)}
```"""
    
    log = state.get("log", []) + execution_log
    
    return {
        "observations": observations,
        "draft": draft,
        "log": log
    }

def node_coding_verifier(state: CodingAgentState) -> CodingAgentState:
    """
    ✅ Verification Phase: Review results and finalize the response.
    Ensures quality and adds helpful context for the user.
    """
    print("\n" + "="*60)
    print("✅ VERIFICATION PHASE: Finalizing your response...")
    print("="*60 + "\n")
    
    draft = state.get("draft", "")
    observations = state.get("observations", [])
    
    # Analyze execution results
    total_steps = len(observations)
    successful_steps = sum(1 for obs in observations if obs.get("success", False))
    failed_steps = total_steps - successful_steps
    
    # Build status summary
    status_summary = format_section_header("Execution Summary", "📊") + f"""

**Total Steps**: {total_steps}
**Successful**: {successful_steps} ✅
**Failed**: {failed_steps} ❌
"""
    
    # Add warnings for errors
    if failed_steps > 0:
        status_summary += f"\n⚠️  **Note**: {failed_steps} step(s) encountered errors. Review the details below.\n"
    
    # Combine status with draft
    final = status_summary + "\n" + draft
    
    # Add helpful footer
    final += f"\n\n{format_section_header('Need Help?', '💡')}\n"
    final += "- Modify the code and run again\n"
    final += "- Ask me to explain any part\n"
    final += "- Request additional features or improvements\n"
    
    print("✅ Response finalized and ready!\n")
    
    return {
        "final": final,
        "approved": True
    }

# ==================== Graph Builder ====================
def build_coding_agent_graph():
    """
    🏗️  Construct the coding agent workflow graph.
    Creates a pipeline: Planning → Execution → Verification
    """
    workflow = StateGraph(CodingAgentState)
    
    # Add processing nodes
    workflow.add_node("coding_planner", node_coding_planner)
    workflow.add_node("coding_executor", node_coding_executor)
    workflow.add_node("coding_verifier", node_coding_verifier)
    
    # Define workflow sequence
    workflow.set_entry_point("coding_planner")
    workflow.add_edge("coding_planner", "coding_executor")
    workflow.add_edge("coding_executor", "coding_verifier")
    workflow.add_edge("coding_verifier", END)
    
    return workflow.compile()

# ==================== Main Entry Point ====================
def tool_coding_agent(user_input: str) -> str:
    """
    🤖 Coding Agent Tool - Main Entry Point
    
    Handles all coding-related tasks through a structured workflow:
    1. Plans the task by breaking it into steps
    2. Executes each step using appropriate tools
    3. Verifies results and generates a user-friendly response
    
    Args:
        user_input: The user's coding request or question
        
    Returns:
        A formatted string containing the complete response
    """
    print("\n" + "="*60)
    print("🤖 CODING AGENT ACTIVATED")
    print("="*60)
    print(f"📨 Request: {user_input[:100]}{'...' if len(user_input) > 100 else ''}\n")
    
    try:
        # Build and execute the workflow graph
        coding_graph = build_coding_agent_graph()
        
        # Initialize state with all required fields
        initial_state = {
            "user_input": user_input,
            "plan": [],
            "observations": [],
            "draft": "",
            "final": "",
            "approved": False,
            "log": []
        }
        
        # Run the workflow
        result = coding_graph.invoke(initial_state)
        
        # Extract and return the final response
        final_output = result.get("final", format_section_header("Error", "❌") + 
                                 "\n\nThe coding agent did not produce a final result. Please try again.")
        
        print("\n" + "="*60)
        print("🎉 CODING AGENT COMPLETED")
        print("="*60 + "\n")
        
        return final_output
        
    except Exception as e:
        error_msg = format_section_header("Agent Error", "❌") + f"""

An unexpected error occurred while processing your request:

{format_error_message(str(e))}

💡 **Suggestions**:
- Check if all required tools are available
- Verify your request is clear and specific
- Try breaking down complex requests into smaller tasks

🔧 **Technical Details**:
```
{str(e)}
```"""
        
        print(f"\n❌ Fatal Error: {str(e)}\n")
        return error_msg