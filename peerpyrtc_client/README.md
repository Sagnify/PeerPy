# peerpyrtc-client

**Socket.io-compatible WebRTC client for building serverless, real-time peer-to-peer applications.**

This package provides a Socket.io-like JavaScript client that replaces WebSockets with true peer-to-peer WebRTC DataChannels. Build chat apps, games, collaborative tools, and real-time dashboards without persistent server connections.

This package contains the **frontend client**. It requires a backend running the `peerpyrtc` Python library.

## 🚀 Key Features

-   **🔄 Socket.io Compatible**: Drop-in replacement with `emit()`, `broadcast()`, and event-driven architecture
-   **⚡ Serverless P2P**: True peer-to-peer after initial signaling - no persistent server needed
-   **🎯 Real-time Peer Management**: Automatic join/leave detection, host election, room state sync
-   **🛡️ Production Ready**: Built-in TURN servers, reconnection, error handling, and failover
-   **📡 Event-Driven**: Comprehensive callback system for peer events and room management
-   **🎮 Multi-Purpose**: Perfect for chat, gaming, collaboration, IoT, trading, video conferencing

## Installation

```bash
npm install peerpyrtc-client
```

## 🚀 Quick Start (Socket.io Style)

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
*Note: This code assumes you are using a bundler like Webpack, Rollup, or Vite to handle the `npm` package import and that a compatible `peerpyrtc` backend is running and accessible.*

## Frontend API Reference

### `WebRTCConnection`

The main class for managing the WebRTC connection with Socket.io-compatible API.

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

## 📚 Examples

The repository includes production-ready examples:

- **💬 Chat Application**: Multi-room chat with real-time peer tracking
- **🎨 Collaborative Whiteboard**: Real-time drawing synchronization
- **🔊 Echo Server**: Simple connectivity testing

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

**Perfect for**: Chat apps, games, collaboration tools, IoT dashboards, trading platforms, video conferencing, and any real-time application.

---

**Built with ❤️ for developers who want WebSocket performance without WebSocket complexity.**
