import os
import time
import threading
from supabase import create_client, Client
from dotenv import load_dotenv
from agent import run_agent_once # Main agent
from coding import _coding_llm # Cerebras model for rejections

load_dotenv()

print("Starting background worker...")

# --- Supabase Client Initialization ---
url: str = os.environ.get("REACT_APP_SUPABASE_URL")
key: str = os.environ.get("REACT_APP_SUPABASE_ANON_KEY")

if not url or not key:
    raise Exception("Supabase URL and Key must be provided in your .env file.")

supabase: Client = create_client(url, key)
print("Supabase client initialized.")

# --- Worker Logic ---

def process_proposal(proposal_id, prompt, conversation_id):
    """
    Runs the agent in a separate thread to avoid blocking the Realtime listener.
    """
    print(f"\n[WORKER] ✅ Thread started for proposal '{proposal_id}' in conversation '{conversation_id}'.")
    
    try:
        # --- Fetch Conversation History ---
        history = []
        if conversation_id:
            print(f"Fetching history for conversation {conversation_id}...")
            # Fetch messages from the team chat for context
            messages_res = supabase.table('messages').select('sender_id, content').eq('conversation_id', conversation_id).order('created_at').execute()
            
            # Format history for the agent
            for msg in messages_res.data:
                # You might want to map sender_id to a role like 'user' or 'assistant' if needed
                history.append({"role": "user", "content": msg['content']})

        # Run the agent with the prompt from the proposal
        print(f"[WORKER] 🧠 Running agent with prompt: '{prompt}' and {len(history)} history messages.")
        result = run_agent_once(prompt, history)
        final_answer = result.get("final", "Agent finished but no answer was provided.")
        
        # --- Interruption Check ---
        # After the agent finishes, check if the task was interrupted while it was running.
        current_proposal_status = supabase.table('proposals').select('status').eq('id', proposal_id).single().execute().data.get('status')
        
        if current_proposal_status == 'interrupted':
            print(f"[WORKER] 🛑 Task '{proposal_id}' was interrupted by the user. Discarding result.")
            # The status is already 'interrupted', so we don't need to do anything else.
        else:
            print(f"[WORKER] 🤖 Agent finished. Updating proposal '{proposal_id}' with analysis.")
            # Update the proposal in the database with the agent's analysis
            supabase.table('proposals').update({
                'agent_analysis': final_answer,
                'status': 'processed' # Mark as processed to avoid re-running
            }).eq('id', proposal_id).execute()
        
    except Exception as e:
        print(f"[WORKER] ❌ Error processing proposal {proposal_id}: {e}")
        # Optionally update the proposal with an error message
        supabase.table('proposals').update({'agent_analysis': f"An error occurred: {e}", 'status': 'error'}).eq('id', proposal_id).execute()

def process_rejection(proposal_id, prompt):
    """
    Handles fully rejected proposals using the Cerebras model.
    """
    print(f"\n[WORKER] ⚠️ Thread started for REJECTED proposal '{proposal_id}'. Running Cerebras model with prompt: '{prompt}'")
    
    try:
        # Use the specialized Cerebras LLM for this task
        rejection_prompt = f"The following task was rejected by the team. Please analyze why it might have been rejected and suggest an alternative approach or explanation.\n\nRejected Task: \"{prompt}\""
        result = _coding_llm.invoke(rejection_prompt).content
        
        print(f"[WORKER] 🤖 Cerebras model finished. Updating proposal '{proposal_id}' with rejection analysis.")
        
        # Update the proposal with the model's response
        supabase.table('proposals').update({
            'agent_analysis': result,
            'status': 'rejected_processed' # Use a distinct status
        }).eq('id', proposal_id).execute()
        
    except Exception as e:
        print(f"[WORKER] ❌ Error processing rejected proposal {proposal_id}: {e}")
        supabase.table('proposals').update({'agent_analysis': f"An error occurred during rejection processing: {e}", 'status': 'error'}).eq('id', proposal_id).execute()

def handle_proposal_update(payload):
    """
    This function is called when a change is detected in the 'proposals' table.
    """
    print(f"\n[REALTIME] Change detected in 'proposals' table: {payload['eventType']}")
    
    # We only care about updates where the status becomes 'approved'
    if payload['eventType'] == 'UPDATE':
        new_data = payload['new']
        old_data = payload['old']
        
        proposal_id = new_data['id']
        prompt = new_data['title']
        conversation_id = new_data.get('conversation_id')

        # Case 1: Task is approved, run the main agent
        if new_data.get('status') == 'approved' and old_data.get('status') != 'approved':
            threading.Thread(target=process_proposal, args=(proposal_id, prompt, conversation_id)).start()

        # Case 2: Task is fully rejected, run the Cerebras model
        elif new_data.get('status') == 'rejected' and old_data.get('status') != 'rejected':
            threading.Thread(target=process_rejection, args=(proposal_id, prompt)).start()

# --- Realtime Subscription ---

print("Subscribing to proposal updates...")
channel = supabase.channel('proposals-db-changes')
channel.on('postgres_changes', event='*', schema='public', table='proposals', callback=handle_proposal_update).subscribe()

print("Worker is now listening for changes. Press Ctrl+C to exit.")

# Keep the script running to listen for events
while True:
    time.sleep(1)