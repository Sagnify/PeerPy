import logging
from flask import Flask, request, jsonify, send_from_directory

import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from PeerPy import SignalingManager

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("flask-echo-signaling")

app = Flask(__name__)

signaling_manager = SignalingManager()

@app.route("/offer", methods=["POST"])
def handle_offer():
    try:
        data = request.get_json()
        room_name = data.get("room")
        peer_id = data.get("peer_id") 
        offer = data.get("offer")

        if not all([room_name, peer_id, offer]):
            return jsonify({"error": "Missing required fields: room, peer_id, offer"}), 400

        logger.info(f"[OFFER] Received from peer={peer_id}, room={room_name}")
        answer = signaling_manager.offer(room_name, peer_id, offer)
        
        if not answer:
            return jsonify({"error": "Failed to create answer"}), 500

        logger.info(f"[OFFER] Answer created for peer={peer_id}")
        return jsonify({"answer": answer})

    except Exception as e:
        logger.error(f"[OFFER] Error processing offer: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@app.route("/candidate", methods=["POST"])
def handle_candidate():
    try:
        data = request.get_json()
        room_name = data.get("room")
        peer_id = data.get("peer_id")
        candidate = data.get("candidate")

        if not all([room_name, peer_id, candidate]):
            return jsonify({"error": "Missing required fields"}), 400

        logger.info(f"[CANDIDATE] Received for peer={peer_id}, room={room_name}")
        signaling_manager.candidate(room_name, peer_id, candidate)
        
        return jsonify({"status": "ok"}), 200

    except Exception as e:
        logger.error(f"[CANDIDATE] Error processing candidate: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@app.route("/leave", methods=["POST"])
def handle_leave():
    try:
        data = request.get_json()
        room_name = data.get("room")
        peer_id = data.get("peer_id")

        if not all([room_name, peer_id]):
            return jsonify({"error": "Missing required fields"}), 400

        logger.info(f"[LEAVE] Peer={peer_id} leaving room={room_name}")
        signaling_manager.leave(room_name, peer_id)
        return jsonify({"status": "ok"})

    except Exception as e:
        logger.error(f"[LEAVE] Error processing leave: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@app.route("/echo", methods=["POST"])
def handle_echo():
    try:
        data = request.get_json()
        room_name = data.get("room")
        peer_id = data.get("peer_id")
        message = data.get("message")

        if not all([room_name, peer_id, message]):
            return jsonify({"error": "Missing required fields: room, peer_id, message"}), 400

        logger.info(f"[ECHO] Received from peer={peer_id}, room={room_name}: {message}")
        
        # For now, we'll just return the message as a response,
        # and the frontend will handle the "echo" by displaying it.
        return jsonify({"echo_message": message}), 200

    except Exception as e:
        logger.error(f"[ECHO] Error processing echo: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@app.route("/")
def index():
    return send_from_directory(os.path.join(os.path.dirname(__file__)), 'index.html')

@app.route("/PeerPy_Client/<path:path>")
def serve_frontend_lib(path):
    return send_from_directory(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "PeerPy_Client")), path)

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {error}")
    return jsonify({"error": "Internal server error"}), 500

if __name__ == "__main__":
    logger.info("🚀 Starting Flask WebRTC Echo signaling server...")
    app.run(host="0.0.0.0", port=5000, debug=True, threaded=True)