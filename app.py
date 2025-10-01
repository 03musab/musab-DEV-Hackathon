import os
import traceback
from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename

# Import your existing agent logic
from dashboard import run_agent_once, ingest_knowledge_base

# --- Basic Flask App Setup ---
app = Flask(__name__)

# --- CORS Configuration ---
# This allows your React frontend (running on a different port)
# to communicate with this Flask backend.
CORS(app, resources={r"/api/*": {"origins": "http://localhost:3000"}})

# --- File Upload Configuration ---
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


@app.route('/api/chat', methods=['POST'])
def chat():
    """
    Handles chat messages from the user.
    Receives: {"message": "user's question"}
    Returns:  {"answer": "agent's response", "log": [...]}
    """
    data = request.json
    user_input = data.get('message')

    if not user_input:
        return jsonify({"error": "No message provided"}), 400

    print(f"Received message: {user_input}")
    try:
        # The agent will now search the entire knowledge base
        result = run_agent_once(user_input, file_path=None)
        
        # Extract the final answer and the log
        final_answer = result.get("final", "I'm sorry, I encountered an error.")
        log_steps = result.get("log", [])

        return jsonify({
            "answer": final_answer,
            "log": log_steps
        })

    except Exception as e:
        print(f"Error during agent execution: {e}")
        traceback.print_exc()
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

        print(f"File '{filename}' uploaded successfully. Ingesting...")
        try:
            # Ingest the file into the knowledge base
            ingest_status = ingest_knowledge_base(file_path)
            print(ingest_status)
            
            # Now, trigger the agent to process the file with a generic prompt
            status = f"File '{filename}' ingested. You can now ask questions about it."
            return jsonify({"status": status})
        except Exception as e:
            error_msg = "".join(traceback.format_exception_only(type(e), e))
            print(f"❌ Ingestion failed: {error_msg}")
            return jsonify({"error": f"Error ingesting {filename}: {error_msg}"}), 500

if __name__ == '__main__':
    # Note: `debug=True` is for development only.
    # Use a production-ready WSGI server like Gunicorn or Waitress for deployment.
    app.run(host='0.0.0.0', port=5000, debug=True)