# peerpyrtc-client

**Socket.io-compatible WebRTC client for building serverless, real-time peer-to-peer applications.**

This package provides a Socket.io-like JavaScript client that replaces WebSockets with true peer-to-peer WebRTC DataChannels. Build chat apps, games, collaborative tools, and real-time dashboards without persistent server connections.

## 🚀 Key Features

-   **🔄 Socket.io Compatible**: Drop-in replacement with `emit()`, `broadcast()`, and event-driven architecture
-   **⚡ Multi-Room Support**: WebRTCRoomManager for handling multiple rooms simultaneously
-   **🎯 Real-time Peer Management**: Automatic join/leave detection, host election, room state sync
-   **🛡️ Production Ready**: Built-in TURN servers, reconnection, error handling, and failover
-   **📡 Event-Driven**: Comprehensive callback system for peer events and room management
-   **🎮 Multi-Purpose**: Perfect for chat, gaming, collaboration, IoT, trading, video conferencing

## 📦 Installation

```bash
npm install peerpyrtc-client
```

### CDN Usage
```html
<script src="https://unpkg.com/peerpyrtc-client/dist/peerpyrtc.umd.js"></script>
<script>
  const { WebRTCConnection } = window.WebRTCConnection;
  const rtc = new WebRTCConnection("my-room");
  rtc.onOpen = () => rtc.sendMessage("Hello World!");
  rtc.connect();
</script>
```

## 🚀 Quick Start

### Basic Usage (Single Room)
```javascript
import { WebRTCConnection } from 'peerpyrtc-client';

const rtc = new WebRTCConnection("game-room", { debug: true });

// Socket.io-like event handling
rtc.onMessage = (senderId, message, event) => {
  if (event === 'player-move') {
    console.log(`Player ${senderId} moved:`, message);
  } else {
    console.log(`Chat from ${senderId}:`, message);
  }
};

rtc.onOpen = () => {
  console.log("Connected! Peers:", rtc.getPeerCount());
  
  // Send regular message
  rtc.sendMessage("Hello everyone!");
  
  // Emit custom events
  rtc.emit('player-move', { x: 5, y: 3 });
  
  // Broadcast to all peers
  rtc.broadcast('game-start', { level: 1 });
};

// Real-time peer management
rtc.onPeerJoined = (peer) => {
  console.log(`🟢 ${peer.id} joined! Host: ${peer.isHost}`);
};

rtc.onPeerLeft = (peer) => {
  console.log(`🔴 ${peer.id} left the room`);
};

// Connect to room
await rtc.connect();
```

### Multi-Room Management
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

// Join multiple rooms
await manager.joinRooms(['lobby', 'game-1', 'chat-general']);

// Emit to specific room
manager.emit('lobby', 'player-joined', { playerId: 'user123' });

// Send message to specific room
manager.sendMessage('game-1', 'Hello game room!');
```

## 📚 API Reference

### WebRTCConnection

#### Constructor
```javascript
const rtc = new WebRTCConnection(roomName, options)
```
- `roomName`: String - Room identifier
- `options`: Object (optional)
  - `peerId`: String - Custom peer ID (auto-generated if not provided)
  - `debug`: Boolean - Enable debug logging (default: false)
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

### WebRTCRoomManager

#### Constructor
```javascript
const manager = new WebRTCRoomManager(userId, options)
```
- `userId`: String - Unique user identifier
- `options`: Object (optional)
  - `debug`: Boolean - Enable debug logging

#### Multi-Room Methods
```javascript
// Room Management
await manager.joinRoom(roomId, options)        // Join single room
await manager.joinRooms([roomIds])             // Join multiple rooms
await manager.leaveRoom(roomId)                // Leave room
await manager.leaveAllRooms()                  // Leave all rooms

// Smart Messaging
manager.emit(roomId, event, data)              // Emit to specific room
manager.emit(roomId, event, data)              // Emit to specific room
manager.sendMessage(roomId, message)           // Send message to room
manager.sendMessage(roomId, message)           // Send message to room

// Event Handling
manager.on(event, handler)                     // Global event handler
manager.onRoom(roomId, event, handler)         // Room-specific handler

// Status & Info
manager.getStatus()                            // Get all room statuses
manager.getRoom(roomId)                        // Get specific room connection
manager.getRoomIds()                           // Get all joined room IDs
manager.isConnectedTo(roomId)                  // Check room connection
```

## 🎯 Real-World Examples

### Chat Application with Seen Status
```javascript
const rtc = new WebRTCConnection(`chat-${roomId}`);

rtc.onMessage = (senderId, message, event) => {
  if (event === 'user-typing') {
    showTypingIndicator(senderId);
  } else if (event === 'user-active') {
    markMessagesAsSeen(senderId, message.activeTime);
  } else if (event === 'user-joined') {
    showUserJoined(senderId, message.userName);
  } else {
    displayMessage(senderId, message.text);
  }
};

// Send typing indicator
rtc.emit('user-typing', { typing: true });

// Mark messages as seen when user opens chat
rtc.emit('user-active', { 
  activeTime: Date.now(),
  userId: currentUser.id 
});

// Notify when user joins
rtc.emit('user-joined', {
  userId: currentUser.id,
  userName: currentUser.name,
  joinTime: Date.now()
});
```

### Multiplayer Game
```javascript
const game = new WebRTCConnection(`game-${gameId}`);

game.onMessage = (playerId, data, event) => {
  switch(event) {
    case 'player-move':
      updatePlayerPosition(playerId, data.position);
      break;
    case 'player-attack':
      processAttack(playerId, data.target, data.damage);
      break;
    case 'game-state':
      syncGameState(data);
      break;
  }
};

// Send player actions
game.emit('player-move', { position: { x: 100, y: 200 } });
game.emit('player-attack', { target: 'enemy1', damage: 50 });

// Broadcast game events (if you're the host)
if (game.isRoomHost()) {
  game.broadcast('game-state', getCurrentGameState());
}
```

### Multi-Room Chat Manager
```javascript
const chatManager = new WebRTCRoomManager(userId);

// Handle messages from all rooms
chatManager.on('chat-message', (roomId, senderId, message) => {
  displayMessage(roomId, senderId, message.text);
  updateChatList(roomId, message.text, senderId);
});

// Handle seen status updates
chatManager.on('user-active', (roomId, senderId, message) => {
  markMessagesAsSeen(roomId, senderId, message.activeTime);
});

// Join multiple chat rooms
await chatManager.joinRooms(['general', 'random', 'tech-talk']);

// Send message to specific room
chatManager.emit('general', 'chat-message', { 
  text: 'Hello everyone!',
  timestamp: Date.now()
});
```

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

### Connection Drops/Reconnection
**Problem**: Network issues causing disconnections.

**Solution**: Handle reconnection gracefully:
```javascript
rtc.onError = (error) => {
  console.log('Connection error:', error);
  // Will auto-reconnect based on maxReconnectAttempts
};

rtc.onClose = () => {
  console.log('Connection closed');
  // Show offline indicator
};

rtc.onOpen = () => {
  console.log('Connected/Reconnected');
  // Re-sync state, show online indicator
};
```

### Multiple Room Management
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

## 🚀 Production Tips

### Error Handling
```javascript
try {
  await rtc.connect();
} catch (error) {
  console.error('Failed to connect:', error);
  showError('Unable to connect to chat. Please try again.');
}
```

### Performance Optimization
```javascript
// Disable debug in production
const rtc = new WebRTCConnection('room', { 
  debug: process.env.NODE_ENV === 'development' 
});

// Batch multiple events
rtc.emit('batch-update', { 
  events: [
    { type: 'player-move', data: { x: 1, y: 2 } },
    { type: 'player-health', data: { health: 90 } }
  ]
});
```

### Security Best Practices
```javascript
// Validate incoming data
rtc.onMessage = (senderId, message, event) => {
  // Validate sender
  if (!isValidUser(senderId)) {
    console.warn('Invalid sender:', senderId);
    return;
  }
  
  // Validate message structure
  if (event === 'player-move' && !isValidPosition(message.position)) {
    console.warn('Invalid position data');
    return;
  }
  
  // Process valid message
  handleMessage(senderId, message, event);
};
```

## 📝 Version History

- **v0.5.1** - Fixed WebRTCRoomManager event handling
- **v0.5.0** - Added WebRTCRoomManager for multi-room support
- **v0.4.0** - Enhanced connection stability and error handling
- **v0.3.0** - Added peer management and host election
- **v0.2.0** - Socket.io-compatible API
- **v0.1.0** - Initial release

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

## 📄 License

MIT License - see LICENSE file for details.

---

**Built with ❤️ for developers who want WebSocket performance without WebSocket complexity.**