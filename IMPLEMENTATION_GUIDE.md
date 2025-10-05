# Implementation Guide: AI Agent Platform

This document provides a technical overview of the AI Agent Platform, intended for developers on the team. It breaks down the project's structure, explains the role of each key file, and describes the core workflows.

## 1. Project Overview

The project is a collaborative multi-agent AI system. Users interact with a team of specialized AI agents (e.g., a general thinker, a fast coder) that work together to accomplish complex tasks. The system is designed to be transparent, showing its thought process, and requires user approval for key actions.

- **Backend**: Python (Flask, LangGraph)
- **Frontend**: React
- **Core AI**: LangChain with models like Meta LLaMA and Cerebras.

## 2. System Architecture

The architecture is composed of a few key layers:

1.  **Frontend UI (React)**: The user-facing interface where users submit prompts and view results. It communicates with the backend via a REST API.
2.  **Web Server (Flask)**: The API layer that receives user requests, manages file uploads for the knowledge base, and routes tasks to the agent system.
3.  **Agent Orchestrator (LangGraph)**: The "brain" of the system. It's a state machine (a graph) that manages the entire lifecycle of a user request, from initial planning to final verification.
4.  **Specialized Agents & Tools**: These are the "workers." The orchestrator delegates tasks to specialized agents (like the `coding_agent`) or individual tools (like `web_search` or `rag_search`).
5.  **Memory & Knowledge Base (Chroma)**: A vector store that provides the agents with long-term memory and a searchable knowledge base from user-uploaded documents.

---

## 3. Backend Implementation

The backend is written in Python and handles all the core logic.

### `main.py`

*   **Purpose**: The main command-line (CLI) entry point for the application.
*   **Key Logic**:
    *   Uses the `click` library to define commands.
    *   The `serve` command starts the Flask web server.
    *   It's responsible for the initial setup, like loading environment variables and initializing the Chroma vector store for agent memory before the app starts.

### `app.py`

*   **Purpose**: The Flask web server that exposes the agent's capabilities via a REST API.
*   **Key API Endpoints**:
    *   `/api/chat`: The primary endpoint for user interaction. It receives a user's message and conversation history, passes it to the agent system via `run_agent_once`, and returns the final answer.
    *   `/api/upload`: Handles file uploads. It saves the file and calls `ingest_knowledge_base` to process and add its content to the RAG vector store.
    *   `/api/health`, `/api/features`, `/api/status`: Helper endpoints to provide status information and metadata to the frontend.
*   **Configuration**: It uses a `Config` class to manage settings like the upload folder and CORS origins, making it easy to configure through environment variables.

### `agent.py`

*   **Purpose**: This is the heart of the AI system. It defines the main agentic workflow using `LangGraph`.
*   **Key Components**:
    *   **`GraphState`**: A `TypedDict` that defines the "state" of the workflow. It tracks everything from the user's input to the final answer, including plans, observations, and logs.
    *   **Nodes**: Each function starting with `node_` (e.g., `node_planner`, `node_executor`, `node_verifier`) represents a step in the agent's thought process.
        *   `node_direct_answer`: First checks if a simple answer exists in memory.
        *   `node_planner`: Analyzes the user's request and creates a step-by-step plan of which tools to use.
        *   `node_executor`: Executes the tools defined in the plan and gathers the results ("observations").
        *   `node_verifier`: Reviews the draft answer for quality and accuracy. It can approve the answer or send it back for revision.
    *   **`build_graph()`**: This function assembles all the nodes and defines the edges (the flow of logic) between them, creating the final, compiled state machine.
    *   **`run_agent_once()`**: The main entry function called by `app.py`. It initializes the graph with the user's input and history, invokes it, and returns the final result.

### `coding.py`

*   **Purpose**: Defines a self-contained, specialized "Coding Agent." This agent is treated as a **tool** that the main agent in `agent.py` can call for any coding-related task.
*   **Key Logic**:
    *   It has its own `LangGraph` workflow, similar to `agent.py` but focused specifically on coding.
    *   **Nodes**:
        *   `node_coding_planner`: Creates a plan to write, run, or read files.
        *   `node_coding_executor`: Executes the plan using tools like `tool_write_file` and `tool_run_code`.
        *   `node_coding_verifier`: Formats the final output, including code blocks and execution summaries.
    *   **`tool_coding_agent()`**: The main entry point that the primary agent calls. It takes a user's coding request and returns a fully formatted markdown response.

### `tools.py`

*   **Purpose**: A centralized registry for all tools the agents can use.
*   **Key Functions**:
    *   `tool_web_search`: Searches the web using DuckDuckGo.
    *   `tool_calculator`: Evaluates mathematical expressions safely.
    *   `tool_write_file`, `tool_read_file`, `tool_run_code`: Provide file system and code execution capabilities.
    *   `tool_rag_search`: Searches the Chroma vector store for information from uploaded documents.
*   **`TOOLS` Dictionary**: This dictionary maps a tool's name to its function and a description. The Planner agent uses these descriptions to decide which tool is appropriate for a given task.

### `prompts.py`

*   **Purpose**: Contains system prompts that define the "personality" and instructions for the agents.
*   **Note**: While this file exists, most of the core prompts (`PLANNER_SYS`, `EXECUTOR_SYS`, etc.) have been moved directly into `agent.py` for better co-location with the logic that uses them. `prompts.py` currently holds the prompt for the coding agent's planner.

---

## 4. Frontend Implementation

The frontend is a **React application** located in the `frontend/` directory. While the specific file contents are not provided, we can infer its role and functionality from the backend API and `README.md`.

*   **Purpose**: To provide a modern, intuitive, and responsive user interface for interacting with the AI agents.
*   **Key Features**:
    *   **Chat Interface**: A primary panel for sending messages to the agent and displaying its responses.
    *   **Prompt Management**: The UI likely includes features like a "prompt lock" or a cooldown timer to manage interactions.
    *   **Real-time Updates**: The `README.md` mentions a plan to use WebSockets for live chat and status updates, which would provide a more dynamic user experience.
    *   **File Uploads**: An interface to upload documents that get sent to the `/api/upload` backend endpoint.
    *   **Displaying Rich Content**: The frontend is responsible for rendering the markdown-formatted responses from the backend, including code blocks, lists, and headers, to present the information clearly.

## 5. Core Workflow (Example: User asks a question)

1.  **User**: Enters a message in the React frontend and clicks "Send."
2.  **Frontend**: Makes a `POST` request to `/api/chat` on the Flask server, sending the message and conversation history.
3.  **`app.py`**: Receives the request and calls `run_agent_once(user_input, history)`.
4.  **`agent.py` (LangGraph)**:
    a. The graph starts at the `direct_answer` node to check for a quick answer in memory.
    b. If none is found, it proceeds to the `planner` node. The planner analyzes the user's intent and creates a JSON plan (e.g., `{"tool": "web_search", "args": {"query": "..."}}`).
    c. The `executor` node receives the plan, calls the corresponding function from `tools.py`, and collects the result.
    d. The `executor` then uses another LLM call to generate a `draft` answer based on the tool's output.
    e. The `verifier` node checks the draft for correctness. If it's good, it polishes the text and puts it in the `final` state field. If not, it provides feedback and sends the process back to the `planner` for another attempt.
5.  **`app.py`**: Once the graph finishes, `run_agent_once` returns the final state. The `final` answer is extracted.
6.  **Frontend**: The Flask server sends the `final` answer back to the React client, which displays it to the user.