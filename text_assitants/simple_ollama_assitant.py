import os
from flask import Flask, request, Response, render_template, jsonify
from flask_cors import CORS
import ollama
import json
import threading # Used for saving history asynchronously to avoid blocking streams

app = Flask(__name__)
CORS(app) # Enable CORS for all routes

# --- Configuration ---
# OLLAMA_MODEL_NAME = "mistral" # 7B parameter model <--- YOUR MODEL NAME
OLLAMA_MODEL_NAME = "llama3.2"   # 3B parameter model <--- YOUR MODEL NAME
HISTORY_FILE = 'chat_history.json' # File to store chat history

# The system prompt is included at the beginning of every conversation.
# This helps guide the model's behavior. It should NOT be an empty string.
SYSTEM_PROMPT = "You are a friendly, helpful, and concise AI assistant. You greet the user and answer their questions politely."

# --- History Management Helper Functions ---
def load_chat_history():
    """Loads chat history from the JSON file."""
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            try:
                history = json.load(f)
                # Basic validation: ensure it's a list of dicts with 'role' and 'content'
                # and that 'content' is not an empty string.
                if isinstance(history, list) and all(
                    isinstance(m, dict) and 'role' in m and 'content' in m and m['content'] != '' for m in history
                ):
                    return history
                else:
                    print(f"Warning: {HISTORY_FILE} content is invalid or contains empty messages. Starting with empty history.")
                    return []
            except json.JSONDecodeError:
                print(f"Warning: {HISTORY_FILE} is corrupted (JSON decode error). Starting with empty history.")
                return []
    return []

def save_chat_history_async(history_to_save):
    """
    Saves chat history to the JSON file in a non-blocking way.
    This is important for streaming responses, as file I/O won't block the stream.
    """
    def _save():
        try:
            with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
                json.dump(history_to_save, f, indent=2, ensure_ascii=False)
            print(f"Chat history saved to {HISTORY_FILE}")
        except Exception as e:
            print(f"Error saving chat history: {e}")
    
    # Use a separate thread to save history
    thread = threading.Thread(target=_save)
    thread.start()

# --- Flask Routes ---
@app.route('/')
def index():
    """Serves the main HTML page for the chatbot."""
    return render_template('index.html')

@app.route('/ask', methods=['POST'])
def ask_llm_stream():
    """
    Handles incoming chat questions, includes full conversation history,
    streams responses, and saves the interaction to history.
    """
    data = request.json
    question = data.get('question', '').strip() # Get question and strip leading/trailing whitespace
    
    # Server-side validation: Ensure the question is not empty after stripping
    if not question:
        return jsonify({'error': 'Question cannot be empty.'}), 400

    # Load existing history to send to Ollama for context
    current_chat_history = load_chat_history()
    
    # Add the current user's question to the history list
    current_chat_history.append({'role': 'user', 'content': question})

    def generate_tokens():
        full_assistant_response = "" # Accumulate the full response to save to history
        try:
            # Construct the messages list for Ollama.
            # It starts with a system prompt (optional, but good for setting tone),
            # followed by the entire conversation history.
            messages_for_ollama = [{'role': 'system', 'content': SYSTEM_PROMPT}] + current_chat_history
            
            response_generator = ollama.chat(
                model=OLLAMA_MODEL_NAME,
                messages=messages_for_ollama, 
                stream=True # Essential for streaming token by token
            )
            
            for chunk in response_generator:
                if 'content' in chunk['message']:
                    token = chunk['message']['content']
                    full_assistant_response += token # Accumulate token for saving
                    # Format for Server-Sent Events (SSE) for frontend
                    yield f"data: {json.dumps({'token': token})}\n\n"
        except Exception as e:
            error_message = f"Error generating response: {str(e)}"
            print(f"Server-side error during generation: {error_message}")
            yield f"data: {json.dumps({'error': error_message})}\n\n"
        finally:
            # This 'finally' block ensures history is saved after streaming completes
            # or if an error occurs and a partial response was generated.
            if full_assistant_response.strip(): # Only save if a non-empty response was generated
                current_chat_history.append({'role': 'assistant', 'content': full_assistant_response})
                save_chat_history_async(current_chat_history) # Save asynchronously
            else:
                print("Warning: Empty assistant response or generation failed.")

    # Return a streaming response with the correct MIME type for SSE.
    return Response(generate_tokens(), mimetype='text/event-stream')

@app.route('/history', methods=['GET'])
def get_history_route():
    """Returns the full chat history as JSON for the frontend to display."""
    history = load_chat_history()
    return jsonify(history)

@app.route('/clear_history', methods=['POST'])
def clear_history_route():
    """Clears the chat history file and returns a success message."""
    if os.path.exists(HISTORY_FILE):
        try:
            os.remove(HISTORY_FILE)
            print(f"Chat history file {HISTORY_FILE} removed.")
            return jsonify({'success': 'Chat history cleared'}), 200
        except OSError as e:
            print(f"Error clearing history file: {e}")
            return jsonify({'error': f'Failed to clear history: {str(e)}'}), 500
    return jsonify({'success': 'No chat history to clear'}), 200

if __name__ == '__main__':
    print(f"Starting Flask app. Ensure Ollama server is running and model '{OLLAMA_MODEL_NAME}' is available.")
    app.run(host='0.0.0.0', port=5000, debug=True)