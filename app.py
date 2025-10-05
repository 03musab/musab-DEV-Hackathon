# app.py
import os
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

from agent import run_agent_once, ingest_knowledge_base

# --- Flask App Initialization ---

app = Flask(__name__, static_folder='../frontend/build', static_url_path='/')

# Enable CORS for all routes, allowing your frontend to communicate with the backend.
# This is crucial for development when frontend and backend run on different ports.
CORS(app)

# --- Supabase Client Initialization ---
# This makes the Supabase client available to all API endpoints in this file.
from supabase import create_client, Client

url: str = os.environ.get("REACT_APP_SUPABASE_URL")
key: str = os.environ.get("REACT_APP_SUPABASE_ANON_KEY") # Use anon key for server-side actions

if not url or not key:
    raise Exception("Supabase URL and Key must be provided in your .env file for the backend server.")

supabase: Client = create_client(url, key)
print("✅ Supabase client initialized for Flask server.")

# --- API Routes ---

@app.route('/api/chat', methods=['POST'])
def chat():
    """Handles chat messages from the frontend."""
    data = request.json
    user_input = data.get('message', '')
    history = data.get('history', [])
    
    if not user_input:
        return jsonify({"error": "No message provided"}), 400

    result = run_agent_once(user_input, history)
    
    # Ensure the response is JSON serializable
    final_answer = result.get("final", "Sorry, I encountered an issue.")
    agent_log = result.get("log", [])
    
    return jsonify({"answer": final_answer, "log": agent_log})

@app.route('/api/proposal/<int:proposal_id>/interrupt', methods=['POST'])
def interrupt_proposal(proposal_id):
    """Interrupts an in-progress agent task."""
    try:
        # Update the proposal status to 'interrupted'
        # The background worker will see this and discard the agent's result.
        data, count = supabase.table('proposals').update({'status': 'interrupted'}).eq('id', proposal_id).execute()
        return jsonify({"message": "Interruption signal sent."}), 200
    except Exception as e:
        print(f"Error interrupting proposal {proposal_id}: {e}")
        return jsonify({"error": str(e)}), 500

# --- Static File Serving ---

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    """Serves the React frontend."""
    if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    else:
        return send_from_directory(app.static_folder, 'index.html')