import os
import traceback
import logging
from flask import Flask, request, jsonify
from flask_cors import CORS
from langchain_chroma import Chroma
from werkzeug.utils import secure_filename

# Import your existing agent logic
from agent import run_agent_once, ingest_knowledge_base
# Import the core config to access global variables and constants
import core.config


# --- Logging Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Basic Flask App Setup ---
app = Flask(__name__)

# --- Configuration ---
# Best practice: Use environment variables for configuration
class Config:
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', 'uploads')
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', 'http://localhost:3000').split(',')
    DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() in ('true', '1', 't')

app.config.from_object(Config)

# --- CORS Configuration ---
CORS(app, resources={r"/api/*": {"origins": app.config['CORS_ORIGINS']}})

# --- Ensure upload folder exists ---
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# --- Initialize Vector Store on Startup ---
print("🧠 Initializing agent memory vector store for Flask app...")
core.config._vectorstore = Chroma(
    collection_name=core.config.MEM_COLLECTION,
    embedding_function=core.config._embedding_fn,
    persist_directory=core.config.PERSIST_DIR
)
print("✅ Agent memory loaded for Flask app.")

@app.route('/api/health', methods=['GET'])
def health_check():
    """
    Health check endpoint to confirm the API is running.
    """
    return jsonify({"status": "ok"}), 200


@app.route('/api/features', methods=['GET'])
def get_features():
    """
    Provides a list of features for the homepage.
    This is mock data.
    """
    features = [
        {
            "id": 1,
            "icon": "code",
            "title": "Function Calling",
            "description": "The model can call functions and integrate with external tools and APIs, extending its capabilities beyond natural language processing."
        },
        {
            "id": 2,
            "icon": "search",
            "title": "Web Search",
            "description": "The model can perform web searches to find real-time information, answer questions about current events, and access a vast repository of knowledge."
        },
        {
            "id": 3,
            "icon": "file-text",
            "title": "File System Operations",
            "description": "The model can read, write, and modify files on the local file system, enabling it to interact with and manage project files directly."
        }
    ]
    return jsonify(features)
    
@app.route('/api/chat', methods=['POST'])
def chat():
    """
    Handles chat messages from the user.
    Receives: {"message": "user's question", "history": [["user msg", "agent msg"], ...]}
    Returns:  {"answer": "agent's response", "log": [...]}
    """
    data = request.json
    user_input = data.get('message')
    # New: Get the conversation history from the request
    history = data.get('history', [])

    if not user_input:
        return jsonify({"error": "No message provided"}), 400

    logging.info(f"Received message: '{user_input}', with {len(history)} turns in history.")
    try:
        # New: Pass the history to the agent runner
        result = run_agent_once(user_input, history)

        # Extract the final answer and the log
        final_answer = result.get("final", "I'm sorry, I encountered an error.")
        log_steps = result.get("log", [])

        return jsonify({
            "answer": final_answer,
            "log": log_steps
        })

    except Exception as e:
        error_id = os.urandom(8).hex()
        logging.error(f"Error ID [{error_id}] during agent execution: {e}\n{traceback.format_exc()}")
        return jsonify({"error": "An internal error occurred."}), 500

@app.route('/api/status', methods=['GET'])
def status():
    """
    Returns the current status of the agent system.
    In a real-world scenario, this would be dynamic.
    """
    # This is mock data based on your request.
    # In the future, this could be derived from a state management system.
    status_data = {
        "activeAgents": 4,
        "tasksInProgress": 6,
        "systemStatus": "Online",
        "agents": ["Meta LLaMA Agent", "Cerebras Agent", "Research Agent", "Critic Agent"]
    }
    return jsonify(status_data)


@app.route('/api/upload', methods=['POST'])
def upload():
    """
    Handles file uploads for the knowledge base.
    """
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    if file:
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)

        logging.info(f"File '{filename}' uploaded successfully. Ingesting...")
        try:
            # Ingest the file into the knowledge base
            ingest_status = ingest_knowledge_base(file_path)
            logging.info(ingest_status)

            # Now, trigger the agent to process the file with a generic prompt
            status = f"File '{filename}' ingested. You can now ask questions about it."
            return jsonify({"status": status})
        except Exception as e:
            error_id = os.urandom(8).hex()
            logging.error(f"Error ID [{error_id}] during ingestion of '{filename}': {e}\n{traceback.format_exc()}")
            return jsonify({"error": f"Failed to process file '{filename}'. Please contact support."}), 500