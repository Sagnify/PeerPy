from flask import Flask, request, jsonify, send_from_directory
from peerpyrtc import SignalingManager

app = Flask(__name__)
signaling_manager = SignalingManager(debug=True)

# Handle all messages
@app.route("/", methods=["GET"])
def index():
    return send_from_directory('.', 'index.html')


# The print() function is not a coroutine and should not be used with await
# Simply remove the await keyword to make it work correctly
@signaling_manager.message_handler
async def on_message(room: str, peer_id: str, message: str):
   print(f"### Message in {room} from {peer_id}: {message} ###")
# Handle peer events
@signaling_manager.peer_joined_handler
async def on_peer_joined(room: str, peer_id: str, peer_info: dict):
    print(f"🟢 {peer_id} joined {room}")

@signaling_manager.peer_left_handler
async def on_peer_left(room: str, peer_id: str, peer_info: dict):
    print(f"🔴 {peer_id} left {room}")

# Standard WebRTC signaling endpoints
@app.route("/offer", methods=["POST"])
def offer():
    try:
        data = request.json
        result = signaling_manager.offer(data['room'], data['peer_id'], data['offer'])
        return jsonify({"answer": result})
    except Exception as e:
        print(f"Error in offer: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/candidate", methods=["POST"])
def candidate():
    try:
        data = request.json
        signaling_manager.candidate(data['room'], data['peer_id'], data['candidate'])
        return jsonify({"status": "ok"})
    except Exception as e:
        print(f"Error in candidate: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/leave", methods=["POST"])
def leave():
    try:
        data = request.json
        signaling_manager.leave(data['room'], data['peer_id'])
        return jsonify({"status": "ok"})
    except Exception as e:
        print(f"Error in leave: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)