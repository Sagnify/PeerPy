# PeerPyRTC

**A serverless, Socket.io-compatible WebRTC library for building real-time peer-to-peer applications.**

PeerPyRTC is a revolutionary WebRTC DataChannel library that **replaces WebSockets** with true peer-to-peer communication. Build chat apps, games, collaborative tools, and real-time dashboards without persistent server connections.

## 🚀 Key Features

-   **🔄 Socket.io Replacement**: Drop-in replacement with `emit()`, `broadcast()`, and event-driven architecture
-   **⚡ Multi-Room Support**: WebRTCRoomManager for handling multiple rooms simultaneously
-   **🎯 Real-time Peer Management**: Automatic join/leave detection, host election, room state sync
-   **🛡️ Production Ready**: Built-in TURN servers, reconnection, error handling, and failover
-   **🔧 Framework Agnostic**: Works with Flask, FastAPI, Django, Express.js, or any web framework
-   **📡 Event-Driven**: Comprehensive callback system for peer events and room management
-   **🎮 Multi-Purpose**: Perfect for chat, gaming, collaboration, IoT, trading, video conferencing

## 📦 Installation

### Backend (Python)
```bash
pip install peerpyrtc
```

### Frontend (JavaScript)
```bash
npm install peerpyrtc-client
```

### Direct Browser Usage (CDN)
```html
<script src="https://unpkg.com/peerpyrtc-client/dist/peerpyrtc.umd.js"></script>
<script>
  const { WebRTCConnection } = window.WebRTCConnection;
  const rtc = new WebRTCConnection("my-room");
  
  rtc.onOpen = () => rtc.sendMessage("Hello World!");
  rtc.connect();
</script>
```

## 🚀 Quick Start (Socket.io Style)

### Backend (Python + Flask)

```python
from flask import Flask, request, jsonify
from peerpyrtc import SignalingManager

app = Flask(__name__)
signaling_manager = SignalingManager(debug=True)

# Handle all messages
@signaling_manager.message_handler
async def on_message(room: str, peer_id: str, message: str):
    print(f"Message in {room} from {peer_id}: {message}")

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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
```

### Frontend (JavaScript)

#### Single Room Usage
```javascript
import { WebRTCConnection } from 'peerpyrtc-client';

const rtc = new WebRTCConnection("game-room", { debug: true });

// Socket.io-like event handling
rtc.onMessage = (senderId, message, event) => {
  if (event) {
    console.log(`Event [${event}]:`, message);
  } else {
    console.log(`Message from ${senderId}:`, message);
  }
};

// Real-time peer management
rtc.onPeerJoined = (peer) => {
  console.log(`🟢 ${peer.id} joined! Host: ${peer.isHost}`);
};

rtc.onPeerLeft = (peer) => {
  console.log(`🔴 ${peer.id} left the room`);
};

rtc.onOpen = () => {
  console.log("Connected! Peers:", rtc.getPeerCount());
  
  // Send regular message
  rtc.sendMessage("Hello everyone!");
  
  // Emit custom events (like Socket.io)
  rtc.emit('player-move', { x: 5, y: 3 });
  
  // Broadcast to all peers
  rtc.broadcast('game-start', { level: 1 });
};

// Connect to room
await rtc.connect();
```

#### Multi-Room Management
```javascript
import { WebRTCRoomManager } from 'peerpyrtc-client';

const manager = new WebRTCRoomManager("user123", { debug: true });

// Global event handlers (apply to all rooms)
manager.on('chat-message', (roomId, senderId, message) => {
  console.log(`Message in ${roomId} from ${senderId}:`, message);
});

manager.on('user-active', (roomId, senderId, message) => {
  console.log(`User ${senderId} active in ${roomId}`);
});

// Room-specific handlers
manager.onRoom('lobby', 'player-joined', (roomId, senderId, data) => {
  console.log(`Player joined lobby:`, data);
});

// Join multiple rooms
await manager.joinRooms(['lobby', 'game-1', 'chat-general']);

// Auto-join and emit (creates connection if needed)
await manager.autoEmit('new-room', 'welcome', { user: 'Alice' });

// Broadcast to all rooms
manager.broadcastToAll('announcement', { text: 'Server maintenance in 5 min' });
```

## 📚 API Reference

### Frontend API (Socket.io Compatible)

#### Constructor
```javascript
const rtc = new WebRTCConnection(roomName, options)
```
- `roomName`: String - Name of the room to join
- `options`: Object (optional)
  - `peerId`: String - Custom peer ID (auto-generated if not provided)
  - `debug`: Boolean - Enable debug logging
  - `maxReconnectAttempts`: Number - Max reconnection attempts (default: 3)
  - `reconnectDelay`: Number - Delay between reconnections in ms (default: 2000)

#### Core Methods
```javascript
// Connection
await rtc.connect()                    // Connect to room
await rtc.closeConnection()            // Leave room
rtc.isConnected()                      // Check connection status

// Messaging (Socket.io style)
rtc.sendMessage(message)               // Send chat message
rtc.emit(event, data)                  // Emit custom event
rtc.broadcast(event, data)             // Broadcast to all peers

// Room Management
rtc.getRoomPeers()                     // Get all peers in room
rtc.getPeerCount()                     // Get number of peers
rtc.isRoomHost()                       // Check if you're the host
```

#### Event Callbacks
```javascript
// Core Events
rtc.onOpen = () => {}                  // Connection established
rtc.onClose = () => {}                 // Connection closed
rtc.onError = (error) => {}            // Connection error
rtc.onMessage = (senderId, message, event) => {} // Receive message/event

// Peer Management Events
rtc.onPeerJoined = (peer) => {}        // New peer joins
rtc.onPeerLeft = (peer) => {}          // Peer leaves
rtc.onRoomUpdate = (peers) => {}       // Room state changes
rtc.onStatusChange = (status) => {}    // Connection status updates
```

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

### Backend API (`peerpyrtc`)

#### SignalingManager

```python
from peerpyrtc import SignalingManager

# Initialize
signaling_manager = SignalingManager(debug=True)

# Core signaling methods (positional arguments required)
signaling_manager.offer(room: str, peer_id: str, offer: dict) -> dict
signaling_manager.candidate(room: str, peer_id: str, candidate: dict) -> None
signaling_manager.leave(room: str, peer_id: str) -> None

# Room information
signaling_manager.rooms_info() -> dict             # Get all rooms info
signaling_manager.get_room_peers(room_name: str) -> list # Get peers in specific room
```

**Parameters:**
- `room`: String - Room/channel identifier
- `peer_id`: String - Unique identifier for the peer
- `offer`: Dict - WebRTC offer object with SDP
- `candidate`: Dict - ICE candidate object

#### Event Handlers (Decorators)

```python
# Message handling
@signaling_manager.message_handler
async def on_message(room_name: str, sender_id: str, message: str):
    # Process every message sent in any room
    await database.save_message(room_name, sender_id, message)

# Peer lifecycle events
@signaling_manager.peer_joined_handler
async def on_peer_joined(room_name: str, peer_id: str, peer_info: dict):
    # Handle peer joining (real-time, no polling needed)
    print(f"New peer {peer_id} joined {room_name}")
    await notify_other_services(peer_id, 'joined')

@signaling_manager.peer_left_handler
async def on_peer_left(room_name: str, peer_id: str, peer_info: dict):
    # Handle peer leaving (automatic detection)
    print(f"Peer {peer_id} left {room_name}")
    await cleanup_user_data(peer_id)
```

## 🎯 Real-World Use Cases

### 🎮 Gaming Applications
```javascript
// Real-time multiplayer game
rtc.emit('player-move', { x: 100, y: 200, direction: 'north' });
rtc.emit('attack', { target: 'enemy1', damage: 50 });
rtc.broadcast('game-over', { winner: 'player1', score: 1500 });
```

### 📝 Collaborative Tools (Google Docs style)
```javascript
// Document collaboration
rtc.emit('cursor-move', { user: 'Alice', position: 145 });
rtc.emit('text-insert', { position: 100, text: 'Hello', user: 'Bob' });
rtc.broadcast('document-saved', { version: 12, timestamp: Date.now() });
```

### 📹 Video Conferencing
```javascript
// Meeting controls
rtc.emit('audio-toggle', { muted: true, user: 'John' });
rtc.emit('screen-share', { enabled: true, streamId: 'abc123' });
rtc.broadcast('meeting-end', { reason: 'host-left' });
```

### 📊 IoT/Real-time Dashboards
```javascript
// Sensor data and alerts
rtc.emit('sensor-data', { temperature: 25.5, humidity: 60, device: 'sensor1' });
rtc.broadcast('alert', { type: 'warning', message: 'High CPU usage', severity: 'medium' });
```

### 💹 Trading/Financial Apps
```javascript
// Market data and orders
rtc.broadcast('price-update', { symbol: 'BTC', price: 45000, change: '+2.5%' });
rtc.emit('order-placed', { orderId: '123', symbol: 'ETH', amount: 0.5, type: 'buy' });
```

## 📚 Examples

The repository includes production-ready examples:

### 💬 **Chat Application**
- Multi-room chat with real-time peer tracking
- Shows online users with host indicators
- Message persistence and moderation
- **Run**: `cd examples/chat && python app.py`

### 🖥️ **Terminal Chat**
- Backend terminal can participate in chat
- Demonstrates server-to-client messaging
- **Run**: `cd examples/terminal_chat && python app.py`

### 🎨 **Collaborative Whiteboard**
- Real-time drawing synchronization
- Multi-user collaboration
- **Run**: `cd examples/whiteboard && python app.py`

### 🔊 **Echo Server**
- Simple connectivity testing
- Message echo functionality
- **Run**: `cd examples/echo && python app.py`

All examples available at `http://localhost:5000` after running.

## 🎆 Why Choose PeerPyRTC?

### **vs WebSockets**
- ✅ **No server scaling issues** - P2P scales infinitely
- ✅ **Lower latency** - Direct peer connections
- ✅ **Reduced server costs** - No persistent connections
- ✅ **Better performance** - No server bottleneck

### **vs Socket.io**
- ✅ **Same familiar API** - Drop-in replacement
- ✅ **Serverless architecture** - True P2P after signaling
- ✅ **Built-in peer management** - Automatic join/leave detection
- ✅ **Production ready** - TURN servers, reconnection, failover

### **vs Raw WebRTC**
- ✅ **Simple integration** - No WebRTC complexity
- ✅ **Event-driven** - Socket.io-like callbacks
- ✅ **Robust networking** - Built-in error handling
- ✅ **Framework agnostic** - Works with any backend

## 🔧 Common Issues & Solutions

### "Cannot send EVENT - data channel not ready"
**Problem**: Trying to emit events immediately after connection.

**Solution**: Wait for connection to be fully established:
```javascript
rtc.onOpen = () => {
  // Connection is ready, safe to emit
  rtc.emit('user-joined', { userId: 'user123' });
};

// Or use setTimeout for delayed emit
const connection = await rtc.connect();
setTimeout(() => {
  if (rtc.isConnected()) {
    rtc.emit('welcome', { message: 'Hello!' });
  }
}, 1000);
```

### Backend 500 Errors
If you get "unexpected keyword argument" errors:

```python
# ❌ DON'T use **request.json
signaling_manager.offer(**request.json)

# ✅ DO use positional arguments
data = request.json
signaling_manager.offer(data['room'], data['peer_id'], data['offer'])
```

### Multi-Room Management
**Problem**: Managing connections to multiple rooms manually.

**Solution**: Use WebRTCRoomManager:
```javascript
// Instead of managing multiple WebRTCConnection instances
const manager = new WebRTCRoomManager('user123');

// Simple room switching
await manager.joinRoom('room1');
await manager.joinRoom('room2');

// Automatic connection management
manager.emit('room1', 'message', { text: 'Hello room 1' });
manager.emit('room2', 'message', { text: 'Hello room 2' });
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

### Production-Ready Backend Example

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

## 🚀 Get Started

1. **Install**: `pip install peerpyrtc && npm install peerpyrtc-client`
2. **Backend**: Add 3 signaling endpoints (`/offer`, `/candidate`, `/leave`)
3. **Frontend**: Replace Socket.io with `WebRTCConnection`
4. **Deploy**: Your app now scales infinitely with P2P! 🎉

**Perfect for**: Chat apps, games, collaboration tools, IoT dashboards, trading platforms, video conferencing, and any real-time application.

---

**Built with ❤️ for developers who want WebSocket performance without WebSocket complexity.**
