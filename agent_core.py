import gradio as gr
import markdown
import os
import traceback

from dashboard import run_agent_once
from config import upload_file

def run_agent_for_ui(user_input, history):
    print(f"Received input: {user_input}")
    result = run_agent_once(user_input)

    # Get the final answer and the log from the agent's result
    log_steps = result.get("log", [])
    final_answer = result.get("final", "I'm sorry, I encountered an error.")
    
    # Format the log into a collapsible HTML section
    log_html = "<details><summary>🕵️ Click to see Agent's Thought Process</summary><ul>"
    for step in log_steps:
        safe_step = markdown.markdown(step.replace("\n", "<br>"))
        log_html += f"<li>{safe_step}</li>"
    log_html += "</ul></details>"

    # Return both the final answer and the thought process
    return f"{final_answer}\n\n{log_html}"

print("Launching Gradio UI...")

with gr.Blocks() as demo:
    gr.Markdown("## 📘 General AI Agent with Custom Knowledge Base")
    
    with gr.Tab("📂 Upload File"):
        file_input = gr.File(label="Upload documents", file_types=[".txt", ".pdf", ".csv", ".xlsx", ".pptx"], file_count="multiple")
        upload_output = gr.Textbox(label="Ingestion Status")
        file_input.change(upload_file, inputs=file_input, outputs=upload_output)
    
    with gr.Tab("💬 Chat with Agent"):
        gr.ChatInterface(
            fn=run_agent_for_ui,
            title="Chat with AI Agent",
            description="You can now query on your uploaded file."
        )

demo.launch(share=True, debug=True)