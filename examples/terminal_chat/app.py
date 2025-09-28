import logging
import sys
import os
import threading

from flask import Flask, request, jsonify, send_from_directory

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from peerpyrtc import SignalingManager, Broadcaster

# --- Basic Setup ---
logger = logging.getLogger("flask-terminal-chat")
app = Flask(__name__)

# Use debug=True to see all the WebRTC signaling logs
signaling_manager = SignalingManager(debug=False)
broadcaster = Broadcaster(signaling_manager)

# The default room name for this simple chat
DEFAULT_ROOM = "terminal-chat-room"

# --- Terminal Input Handling ---

def terminal_input_loop():
    """
    A loop that runs in a background thread to read from the terminal.
    This allows the backend operator to send messages.
    """
    print("\n\nTerminal chat is ready.")
    print(f"Messages you type here will be sent to the client in room '{DEFAULT_ROOM}'.")
    print("--------------------------------------------------")
    
    while True:
        try:
            message = input("Backend > ")
            if message:
                logger.info(f"Sending message from terminal to room '{DEFAULT_ROOM}': {message}")
                broadcaster.broadcast(DEFAULT_ROOM, message)
        except EOFError:
            # This can happen if the process is killed, just exit the loop
            break

# --- Frontend Message Handling ---

@signaling_manager.message_handler
async def on_frontend_message(room_name: str, sender_id: str, message: str):
    """
    This function is called whenever a message is received from the frontend.
    """
    # Print the message to the backend terminal
    print(f"\nFrontend ({sender_id} in {room_name}) > {message}")
    print("Backend > ", end="", flush=True) # Reprint the input prompt


# --- Standard WebRTC Signaling Endpoints ---

@app.route("/offer", methods=["POST"])
def handle_offer():
    data = request.get_json()
    answer = signaling_manager.offer(data.get("room"), data.get("peer_id"), data.get("offer"))
    return jsonify({"answer": answer})

@app.route("/candidate", methods=["POST"])
def handle_candidate():
    data = request.get_json()
    signaling_manager.candidate(data.get("room"), data.get("peer_id"), data.get("candidate"))
    return jsonify({"status": "ok"})

@app.route("/leave", methods=["POST"])
def handle_leave():
    data = request.get_json()
    signaling_manager.leave(data.get("room"), data.get("peer_id"))
    return jsonify({"status": "ok"})

# --- HTML and JS Serving ---

@app.route("/")
def index():
    return send_from_directory(os.path.join(os.path.dirname(__file__)), 'index.html')

@app.route("/peerpyrtc_client/<path:path>")
def serve_frontend_lib(path):
    return send_from_directory(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "peerpyrtc_client")), path)


if __name__ == "__main__":
    # Start the thread that reads input from the terminal
    input_thread = threading.Thread(target=terminal_input_loop, daemon=True)
    input_thread.start()

    logger.info("🚀 Starting Terminal Chat server...")
    logger.info("Open http://127.0.0.1:5000 in your browser to start.")

    # Run the Flask app
    app.run(host="0.0.0.0", port=5000, debug=False) # Flask's reloader interferes with the input() thread
