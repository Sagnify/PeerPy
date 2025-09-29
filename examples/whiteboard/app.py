import logging
from flask import Flask, request, jsonify, send_from_directory

import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from peerpyrtc import SignalingManager

# Get the logger for this application
logger = logging.getLogger("flask-whiteboard-signaling")

app = Flask(__name__)

# Instantiate the SignalingManager with debug logging enabled
signaling_manager = SignalingManager(debug=True)

# Simulate database for whiteboard actions
class WhiteboardDB:
    def __init__(self):
        self.strokes = []
        self.actions = []
    
    async def save_stroke_start(self, room, user, x, y, color, size):
        stroke_id = len(self.strokes)
        self.strokes.append({
            'id': stroke_id,
            'room': room,
            'user': user,
            'start_x': x,
            'start_y': y,
            'color': color,
            'size': size,
            'points': [(x, y)],
            'timestamp': __import__('time').time()
        })
        print(f"📝 Started stroke {stroke_id} by {user} at ({x}, {y})")
        return stroke_id
    
    async def add_stroke_point(self, stroke_id, x, y):
        if stroke_id < len(self.strokes):
            self.strokes[stroke_id]['points'].append((x, y))
    
    async def save_action(self, room, user, action_type, data=None):
        self.actions.append({
            'room': room,
            'user': user,
            'action': action_type,
            'data': data,
            'timestamp': __import__('time').time()
        })
        print(f"🎨 Action: {user} did {action_type} in {room}")

db = WhiteboardDB()

# Smart message handler that processes different event types appropriately
@signaling_manager.message_handler
async def handle_whiteboard_events(room_name: str, sender_id: str, message: str):
    """Smart handler that processes whiteboard events efficiently"""
    try:
        # Check if it's an emit event (new format)
        if hasattr(message, 'startswith') and message.startswith('{"type":"SYSTEM"'):
            import json
            data = json.loads(message)
            if data.get('action') == 'EVENT':
                event_name = data['payload']['event']
                event_data = data['payload']['data']
                
                if event_name == 'draw':
                    # Only save significant drawing events, not every mouse move
                    # You could batch these or save stroke starts/ends
                    pass  # Skip individual draw points
                elif event_name == 'clear':
                    await db.save_action(room_name, sender_id, 'clear_canvas')
                elif event_name == 'cursor':
                    # Don't save cursor movements to DB
                    pass
                return
        
        # Handle regular messages (if any)
        if message and len(message) < 1000:  # Only save reasonable-sized messages
            await db.save_action(room_name, sender_id, 'message', message)
            
    except Exception as e:
        print(f"Error processing whiteboard event: {e}")

# Optional: Add endpoint to get whiteboard history
@app.route("/whiteboard-history/<room_name>")
def get_whiteboard_history(room_name):
    """Get whiteboard history for a room"""
    room_strokes = [s for s in db.strokes if s['room'] == room_name]
    room_actions = [a for a in db.actions if a['room'] == room_name]
    return jsonify({
        "strokes": room_strokes,
        "actions": room_actions
    })

@app.route("/offer", methods=["POST"])
def handle_offer():
    try:
        data = request.get_json()
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
    try:
        data = request.get_json()
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
    try:
        data = request.get_json()
        room_name = data.get("room")
        peer_id = data.get("peer_id")

        if not all([room_name, peer_id]):
            return jsonify({"error": "Missing required fields"}), 400

        signaling_manager.leave(room_name, peer_id)
        return jsonify({"status": "ok"})

    except Exception as e:
        logger.error(f"[LEAVE] Error processing leave: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@app.route("/")
def index():
    return send_from_directory(os.path.join(os.path.dirname(__file__)), 'index.html')

@app.route("/peerpyrtc_client/<path:path>")
def serve_frontend_lib(path):
    return send_from_directory(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "peerpyrtc_client")), path)

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {error}")
    return jsonify({"error": "Internal server error"}), 500

if __name__ == "__main__":
    logger.info("🚀 Starting Flask WebRTC Whiteboard signaling server...")
    app.run(host="0.0.0.0", port=5000, debug=True, threaded=True)
