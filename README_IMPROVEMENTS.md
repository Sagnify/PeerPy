# README Improvements for PeerPyRTC

## Issues Found and Suggested Fixes:

### 1. Backend Signaling Endpoints (CRITICAL FIX)

**Current README shows (INCORRECT):**
```python
@app.route("/offer", methods=["POST"])
def offer():
    return jsonify(signaling_manager.offer(**request.json))
```

**Should be (CORRECT):**
```python
@app.route("/offer", methods=["POST"])
def offer():
    data = request.json
    result = signaling_manager.offer(data['room'], data['peer_id'], data['offer'])
    return jsonify({"answer": result})

@app.route("/candidate", methods=["POST"])
def candidate():
    data = request.json
    signaling_manager.candidate(data['room'], data['peer_id'], data['candidate'])
    return jsonify({"status": "ok"})

@app.route("/leave", methods=["POST"])
def leave():
    data = request.json
    signaling_manager.leave(data['room'], data['peer_id'])
    return jsonify({"status": "ok"})
```

### 2. Add SignalingManager Method Signatures Section

```markdown
#### SignalingManager Method Signatures

```python
# Core signaling methods (positional arguments required)
signaling_manager.offer(room: str, peer_id: str, offer: dict) -> dict
signaling_manager.candidate(room: str, peer_id: str, candidate: dict) -> None
signaling_manager.leave(room: str, peer_id: str) -> None

# Room information methods
signaling_manager.rooms_info() -> dict
signaling_manager.get_room_peers(room_name: str) -> list
```

**Parameters:**
- `room`: String - Room/channel identifier
- `peer_id`: String - Unique identifier for the peer
- `offer`: Dict - WebRTC offer object with SDP
- `candidate`: Dict - ICE candidate object
```

### 3. Clarify peer.isHost Documentation

**Current:**
```javascript
rtc.onPeerJoined = (peer) => {
  console.log(`🟢 ${peer.id} joined! Host: ${peer.isHost}`);
};
```

**Add explanation:**
```markdown
#### Peer Object Properties

When a peer joins or leaves, the peer object contains:

```javascript
{
  id: "peer-abc123",           // Unique peer identifier
  isHost: true,                // Whether THIS peer is the room host
  // ... other properties
}
```

**Host Management:**
- First peer to join becomes the host (`isHost: true`)
- If host leaves, another peer is automatically elected
- Use `rtc.isRoomHost()` to check if YOU are the host
- Use `peer.isHost` to check if a specific peer is the host
```

### 4. Add Common Issues Section

```markdown
## 🔧 Common Issues & Solutions

### Backend 500 Errors
If you get "unexpected keyword argument" errors:

```python
# ❌ DON'T use **request.json
signaling_manager.offer(**request.json)

# ✅ DO use positional arguments
data = request.json
signaling_manager.offer(data['room'], data['peer_id'], data['offer'])
```

### CDN Usage
```html
<!-- ✅ Correct CDN usage -->
<script src="https://unpkg.com/peerpyrtc-client/dist/peerpyrtc.umd.js"></script>
<script>
  const { WebRTCConnection } = window.WebRTCConnection;
  // NOT: window.WebRTCConnection.WebRTCConnection
</script>
```
```

### 5. Add Error Handling Example

```markdown
#### Production-Ready Backend Example

```python
from flask import Flask, request, jsonify
from peerpyrtc import SignalingManager

app = Flask(__name__)
signaling_manager = SignalingManager(debug=False)  # Set to False in production

@app.route("/offer", methods=["POST"])
def offer():
    try:
        data = request.json
        if not all(k in data for k in ['room', 'peer_id', 'offer']):
            return jsonify({"error": "Missing required parameters"}), 400
            
        result = signaling_manager.offer(data['room'], data['peer_id'], data['offer'])
        return jsonify({"answer": result})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/candidate", methods=["POST"])
def candidate():
    try:
        data = request.json
        if not all(k in data for k in ['room', 'peer_id', 'candidate']):
            return jsonify({"error": "Missing required parameters"}), 400
            
        signaling_manager.candidate(data['room'], data['peer_id'], data['candidate'])
        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/leave", methods=["POST"])
def leave():
    try:
        data = request.json
        if not all(k in data for k in ['room', 'peer_id']):
            return jsonify({"error": "Missing required parameters"}), 400
            
        signaling_manager.leave(data['room'], data['peer_id'])
        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
```
```

## Summary

The main issues are:
1. **Incorrect backend endpoint examples** (causes 500 errors)
2. **Missing method signature documentation**
3. **Unclear peer.isHost explanation**
4. **No error handling examples**
5. **No troubleshooting section**

These improvements would prevent the confusion you experienced and make the library much easier to use correctly.