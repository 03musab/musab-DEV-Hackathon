# 🤖 AI Agent Platform

> A collaborative multi-agent AI system where specialized agents work together to accomplish complex tasks



## 🎯 Project Vision

We're creating a platform where users interact with multiple AI agents, each optimized for a specific type of task—like analyzing spreadsheets, building slide decks, or summarizing web content. Think of it as a digital task force of AI specialists working in parallel.

The platform features a unique collaborative workflow where tasks must be approved by multiple users before being sent to an AI agent for processing, ensuring human-in-the-loop oversight.

## ✨ Features

### 🧠 Explaining Thought Process
- **Multimodal Agent** (✅ Implemented)
- Transparent reasoning with step-by-step explanations
- Visual representation of decision-making processes

### 🎨 Modern User Interface
- React-based GUI (inspired by Manus.ai)
- Flask backend integration with Python core
- Intuitive, responsive design for seamless interaction

### 💭 Memory & Context Management
- **Human-in-the-Loop** system for approval workflows
- Persistent memory across sessions
- Context-aware conversations that remember previous chats

### 🔬 AI-Driven Research Collaborator
Imagine a "research team in a box":
- **Literature Review Agent**: Searches and summarizes relevant research
- **Critic Agent**: Peer-review style analysis of findings
- **Hypothesis Generator**: Suggests novel research directions
- **Paper Drafter**: Compiles findings into structured reports

### 📊 AI-Powered Dashboard
Interactive visual outputs alongside conversational AI:
- Real-time graph generation
- Mind map creation
- Dynamic to-do lists and Kanban boards
- **Example**: Say "plan my week" → generates a visual calendar/Kanban view

### ⚡ Autonomous Task Execution
- **Workflow Orchestration**: Executes real-world tasks via APIs
  - Send emails
  - Schedule meetings
  - Fetch live data (stocks, weather, etc.)
- **User Confirmation Required**: All actions require explicit approval
- **Integration Support**: N8N / Zapier pipeline compatibility

## 🤖 Core Agent Capabilities

### 🧠 Meta LLaMA Agent – The Smart Thinker

**What it does:**
- **Reasoning**: Performs complex logical deductions and problem-solving
- **Summarization**: Condenses large volumes of text into concise summaries
- **General NLP Tasks**: Sentiment analysis, entity recognition, translation
- **Learning & Adaptation**: Continuously refines performance through feedback

**Best for:** Understanding, analyzing, and thinking through complex problems

### ⚡ Cerebras Agent – The Fast Worker

**What it does:**
- **High-Speed Inference**: Executes computationally intensive tasks with minimal latency
- **Large Prompt Handling**: Optimized for lengthy and detailed inputs
- **Code Generation & Optimization**: Generates high-quality code and suggests improvements
- **Parallel Processing**: Handles multiple demanding operations simultaneously

**Best for:** Building, executing, and processing at scale

---

**Together, they form a complete team:**
- 🧠 One thinks and understands
- ⚡ One builds and executes fast

## 🏗️ System Architecture

### Components Overview

| Component | Role |
|-----------|------|
| **Frontend UI** | Shared interface with prompt lock, cooldown timer, and chat panel |
| **Agent Orchestrator** | Routes tasks to appropriate agents and manages consent logic |
| **Meta LLaMA Agent** | Handles reasoning, summarization, and general NLP tasks |
| **Cerebras Agent** | Executes high-speed inference for large prompts or code generation |
| **Docker MCP Gateway** | Hosts isolated tools (sandbox, file manager, visualizer) securely |
| **Shared Memory Store** | Tracks session history, agent states, and user approvals |

### Current Implementation

The existing codebase leverages:
- **A custom agent framework** for agent orchestration and workflow management
- **Flask & React** for the backend API and frontend UI
- **Supabase** for the database, real-time updates, and authentication.
- **A modular tool system** for extensible agent capabilities.

### Future Architecture
The project is designed to evolve towards a more scalable architecture, potentially incorporating:
- **FastAPI** for a high-performance backend.
- **WebSockets** for even faster real-time communication.
- **Cloud-hosted Vector DB** for scalable memory and RAG.
- **Docker-based tool isolation** for enhanced security.

## 🚀 Getting Started

### Prerequisites

```bash
- Python 3.9+
- Node.js 16+
- Docker (for isolated tool execution)
```

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/ai-agent-platform.git
cd ai-agent-platform

# Install Python dependencies
pip install -r requirements.txt

# Install frontend dependencies
cd frontend
npm install
```

### Running the Application

**IMPORTANT**: The backend requires **two separate terminal windows** to run correctly: one for the web server and one for the AI task processor.

```bash
# In your first terminal, start the Flask web server:
# This serves the website and handles basic API requests.
python app.py

# In your second terminal, start the background worker:
# This is the process that listens for approved tasks and runs the AI agent.
# If this is not running, the agent will never respond to approved tasks.
python background_worker.py

# In a third terminal, start the React frontend development server:
cd frontend
npm start
```

## 🛠️ Technology Stack

- **Backend**: Python, FastAPI, LangGraph
- **Frontend**: React, TypeScript
- **AI Models**: Meta LLaMA, Cerebras
- **Database**: PostgreSQL, Redis, Supabase
- **Vector Store**: Chroma → Cloud-hosted solution
- **Authentication**: Firebase Auth / Clerk
- **Automation**: N8N / Zapier integration
- **Containerization**: Docker

## 📋 Roadmap

- [x] Core agent reasoning loop
- [x] Multimodal agent implementation
- [x] React-based UI migration
- [x] Flask backend integration
- [ ] Memory persistence system
- [ ] Research collaborator agents
- [ ] Visual dashboard generation
- [ ] Task execution with API integrations
- [ ] Multi-user approval workflow
- [ ] Docker-based tool isolation
- [ ] Cloud deployment

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 📧 Contact

For questions or feedback, please open an issue or reach out to the maintainers.

---

**Built with ❤️**