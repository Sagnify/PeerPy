import logging
from flask import Flask, request, jsonify, send_from_directory

import sys
import os
import asyncio

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from peerpyrtc import SignalingManager

# Get the logger for this application
logger = logging.getLogger("flask-signaling")

app = Flask(__name__)

# Instantiate the SignalingManager with debug logging enabled
signaling_manager = SignalingManager(debug=True)

# Assume 'db' is an initialized database client/session
# For demonstration, let's just simulate a database operation
class MockDatabase:
    async def save_chat_message(self, room_name, sender_id, message):
        print(f"--- SIMULATING DB SAVE --- Room: {room_name}, Sender: {sender_id}, Message: {message}")
        await asyncio.sleep(0.1) # Simulate async DB call
        print("--- DB SAVE COMPLETE ---")

db = MockDatabase() # In a real app, this would be your actual DB connection

# --- Backend Message Handler (using decorator) ---
@signaling_manager.message_handler
async def custom_chat_message_handler(room_name: str, sender_id: str, message: str):
    logger.info(f"[CUSTOM_BACKEND_MESSAGE] Room: {room_name}, Sender: {sender_id}, Message: {message}")
    await db.save_chat_message(room_name, sender_id, message)

@signaling_manager.peer_joined_handler
async def on_peer_joined(room_name: str, peer_id: str, peer_info: dict):
    logger.info(f"[PEER_JOINED] {peer_id} joined room {room_name}")
    print(f"🟢 Peer {peer_id} joined {room_name} at {peer_info.get('joinTime')}")

@signaling_manager.peer_left_handler
async def on_peer_left(room_name: str, peer_id: str, peer_info: dict):
    logger.info(f"[PEER_LEFT] {peer_id} left room {room_name}")
    print(f"🔴 Peer {peer_id} left {room_name}")
# -------------------------------------------------

@app.route("/room-status/<room>")
def get_room_status(room):
    """Get the list of peers in a room with metadata"""
    peers = signaling_manager.get_room_peers(room)
    return jsonify({
        "peers": peers,
        "count": len(peers),
        "host_id": signaling_manager.rooms[room].get_host_id() if room in signaling_manager.rooms else None
    })

@app.route("/offer", methods=["POST"])
def handle_offer():
    """Handle WebRTC offer from client"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No JSON data received"}), 400
        
        room_name = data.get("room")
        peer_id = data.get("peer_id") 
        offer = data.get("offer")

        if not all([room_name, peer_id, offer]):
            return jsonify({"error": "Missing required fields: room, peer_id, offer"}), 400

        answer = signaling_manager.offer(room_name, peer_id, offer)
        
        if not answer:
            return jsonify({"error": "Failed to create answer"}), 500

        return jsonify({"answer": answer})

    except Exception as e:
        logger.error(f"[OFFER] Error processing offer: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@app.route("/candidate", methods=["POST"])
def handle_candidate():
    """Handle ICE candidate from client"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No JSON data received"}), 400
            
        room_name = data.get("room")
        peer_id = data.get("peer_id")
        candidate = data.get("candidate")

        if not all([room_name, peer_id, candidate]):
            return jsonify({"error": "Missing required fields"}), 400

        signaling_manager.candidate(room_name, peer_id, candidate)
        
        return jsonify({"status": "ok"}), 200

    except Exception as e:
        logger.error(f"[CANDIDATE] Error processing candidate: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@app.route("/leave", methods=["POST"])
def handle_leave():
    """Handle peer leaving room"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No JSON data received"}), 400
            
        room_name = data.get("room")
        peer_id = data.get("peer_id")

        if not all([room_name, peer_id]):
            return jsonify({"error": "Missing required fields"}), 400

        signaling_manager.leave(room_name, peer_id)

        return jsonify({"status": "ok"}), 200

    except Exception as e:
        logger.error(f"[LEAVE] Error processing leave: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@app.route("/rooms", methods=["GET"])
def list_rooms():
    """List all active rooms (for debugging)"""
    room_info = signaling_manager.rooms_info()
    return jsonify(room_info)

@app.route("/")
def index():
    """Serve the main HTML page"""
    # Serve index.html from the examples/chat directory
    return send_from_directory(os.path.join(os.path.dirname(__file__)), 'index.html')

@app.route("/peerpyrtc_client/<path:path>")
def serve_frontend_lib(path):
    """Serve the peerpyrtc_client library files"""
    # Serve files from the peerpyrtc_client directory
    return send_from_directory(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "peerpyrtc_client")), path)

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {error}")
    return jsonify({"error": "Internal server error"}), 500

if __name__ == "__main__":
    # The library now handles its own logging setup when debug=True
    logger.info("🚀 Starting Flask WebRTC DataChannel signaling server...")
    logger.info("📡 WebRTC signaling endpoints available:")
    logger.info("   POST /offer - Handle WebRTC offers")
    logger.info("   POST /candidate - Handle ICE candidates") 
    logger.info("   POST /leave - Handle peer disconnection")
    logger.info("   GET /rooms - List active rooms")
    logger.info("   GET / - Serve chat interface")
    
    # Set debug=True for Flask's reloader and debugger
    app.run(host="0.0.0.0", port=5000, debug=True, threaded=True)
