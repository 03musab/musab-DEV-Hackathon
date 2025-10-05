# main.py
import os
import click
from langchain_chroma import Chroma

# --- Core Imports ---
# By importing config first, we ensure all environment variables and constants are loaded.
import core.config

# Now, we can safely import other components that might use the config.
from app import app
from agent import run_agent_once

@click.group()
def cli():
    """AI Agent Platform CLI"""
    # Initialize the memory vector store and assign it to the global variable in the core config.
    print("🧠 Initializing agent memory vector store...")
    core.config._vectorstore = Chroma(
        collection_name=core.config.MEM_COLLECTION,
        embedding_function=core.config._embedding_fn,
        persist_directory=core.config.PERSIST_DIR
    )
    print("✅ Agent memory loaded.")

@cli.command()
def serve():
    """Starts the Flask web server."""
    app.run(host='0.0.0.0', port=5000, debug=app.config['DEBUG'])

@cli.command()
@click.argument('user_input', required=False)
def chat(user_input):
    """Starts an interactive chat session with the agent."""
    history = []
    if not user_input:
        user_input = click.prompt("User")
    result = run_agent_once(user_input, history)
    print("Agent:", result.get("final", "Sorry, I don't have an answer."))


if __name__ == '__main__':
    cli()