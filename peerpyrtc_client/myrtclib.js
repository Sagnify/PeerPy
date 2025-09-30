// Multi-Room Manager for handling multiple WebRTC connections
export class WebRTCRoomManager {
  constructor(userId, options = {}) {
    this.userId = userId;
    this.debug = options.debug || false;
    this.connections = new Map(); // roomId -> WebRTCConnection
    this.globalHandlers = new Map(); // event -> handler
    this.roomHandlers = new Map(); // roomId -> Map(event -> handler)
    
    // Global event callbacks
    this.onRoomJoined = () => {};
    this.onRoomLeft = () => {};
    this.onConnectionChange = () => {};
  }
  
  _log(...args) {
    if (this.debug) {
      console.log('[ROOM-MANAGER]', ...args);
    }
  }
  
  // Join multiple rooms at once
  async joinRooms(roomIds) {
    const results = await Promise.allSettled(
      roomIds.map(roomId => this.joinRoom(roomId))
    );
    return results.map((result, index) => ({
      roomId: roomIds[index],
      success: result.status === 'fulfilled',
      connection: result.status === 'fulfilled' ? result.value : null,
      error: result.status === 'rejected' ? result.reason : null
    }));
  }
  
  // Join a single room
  async joinRoom(roomId, roomOptions = {}) {
    if (this.connections.has(roomId)) {
      this._log(`Already connected to room: ${roomId}`);
      return this.connections.get(roomId);
    }
    
    this._log(`Joining room: ${roomId}`);
    
    const connection = new WebRTCConnection(roomId, {
      peerId: this.userId,
      debug: this.debug,
      ...roomOptions
    });
    
    // Set up event forwarding
    this._setupConnectionHandlers(connection, roomId);
    
    try {
      await connection.connect();
      this.connections.set(roomId, connection);
      this.onRoomJoined(roomId, connection);
      this._log(`Successfully joined room: ${roomId}`);
      return connection;
    } catch (error) {
      this._log(`Failed to join room ${roomId}:`, error);
      throw error;
    }
  }
  
  // Leave a room
  async leaveRoom(roomId) {
    const connection = this.connections.get(roomId);
    if (connection) {
      await connection.closeConnection();
      this.connections.delete(roomId);
      this.roomHandlers.delete(roomId);
      this.onRoomLeft(roomId);
      this._log(`Left room: ${roomId}`);
    }
  }
  
  // Leave all rooms
  async leaveAllRooms() {
    const roomIds = Array.from(this.connections.keys());
    await Promise.all(roomIds.map(roomId => this.leaveRoom(roomId)));
  }
  
  // Emit to specific room
  emit(roomId, event, data) {
    const connection = this.connections.get(roomId);
    if (connection && connection.isConnected()) {
      connection.emit(event, data);
      return true;
    }
    this._log(`Cannot emit to room ${roomId}: not connected`);
    return false;
  }
  
  // Broadcast to all rooms
  broadcastToAll(event, data) {
    let successCount = 0;
    for (const [roomId, connection] of this.connections) {
      if (connection.isConnected()) {
        connection.emit(event, data);
        successCount++;
      }
    }
    this._log(`Broadcasted to ${successCount}/${this.connections.size} rooms`);
    return successCount;
  }
  
  // Send message to specific room
  sendMessage(roomId, message) {
    const connection = this.connections.get(roomId);
    if (connection && connection.isConnected()) {
      connection.sendMessage(message);
      return true;
    }
    return false;
  }
  
  // Global event handler (applies to all rooms)
  on(event, handler) {
    this.globalHandlers.set(event, handler);
    // Apply to existing connections
    for (const [roomId, connection] of this.connections) {
      this._applyHandler(connection, roomId, event, handler);
    }
  }
  
  // Auto-join room and emit (handles connection automatically)
  async autoEmit(roomId, event, data) {
    if (!this.isConnectedTo(roomId)) {
      this._log(`Auto-joining room ${roomId} for emit`);
      await this.joinRoom(roomId);
    }
    return this.emit(roomId, event, data);
  }
  
  // Join room with automatic event setup
  async joinRoomWithEvents(roomId, eventHandlers = {}, roomOptions = {}) {
    // Set up room-specific handlers before joining
    Object.entries(eventHandlers).forEach(([event, handler]) => {
      this.onRoom(roomId, event, handler);
    });
    
    return await this.joinRoom(roomId, roomOptions);
  }
  
  // Room-specific event handler
  onRoom(roomId, event, handler) {
    if (!this.roomHandlers.has(roomId)) {
      this.roomHandlers.set(roomId, new Map());
    }
    this.roomHandlers.get(roomId).set(event, handler);
    
    // Apply to existing connection if available
    const connection = this.connections.get(roomId);
    if (connection) {
      this._applyHandler(connection, roomId, event, handler);
    }
  }
  
  // Get connection status for all rooms
  getStatus() {
    const status = {};
    for (const [roomId, connection] of this.connections) {
      status[roomId] = {
        connected: connection.isConnected(),
        peerCount: connection.getPeerCount(),
        isHost: connection.isRoomHost(),
        connectionStatus: connection.getConnectionStatus()
      };
    }
    return status;
  }
  
  // Get specific room connection
  getRoom(roomId) {
    return this.connections.get(roomId);
  }
  
  // Get all room IDs
  getRoomIds() {
    return Array.from(this.connections.keys());
  }
  
  // Check if connected to room
  isConnectedTo(roomId) {
    const connection = this.connections.get(roomId);
    return connection ? connection.isConnected() : false;
  }
  
  // Private methods
  _setupConnectionHandlers(connection, roomId) {
    // Forward connection events with room context
    connection.onOpen = () => {
      this._log(`Room ${roomId} connected`);
      this.onConnectionChange(roomId, 'connected');
    };
    
    connection.onClose = () => {
      this._log(`Room ${roomId} disconnected`);
      this.onConnectionChange(roomId, 'disconnected');
    };
    
    connection.onError = (error) => {
      this._log(`Room ${roomId} error:`, error);
      this.onConnectionChange(roomId, 'error', error);
    };
    
    // Apply global handlers
    for (const [event, handler] of this.globalHandlers) {
      this._applyHandler(connection, roomId, event, handler);
    }
    
    // Apply room-specific handlers
    const roomHandlers = this.roomHandlers.get(roomId);
    if (roomHandlers) {
      for (const [event, handler] of roomHandlers) {
        this._applyHandler(connection, roomId, event, handler);
      }
    }
  }
  
  _applyHandler(connection, roomId, event, handler) {
    // Store original handler if it exists
    if (!connection._originalOnMessage) {
      connection._originalOnMessage = connection.onMessage;
    }
    
    connection.onMessage = (senderId, message, eventType) => {
      // Call original handler first
      if (connection._originalOnMessage) {
        connection._originalOnMessage(senderId, message, eventType);
      }
      
      // Call specific handler if event matches
      if (eventType === event) {
        handler(roomId, senderId, message, eventType);
      }
      
      // Call global handlers for any event
      for (const [globalEvent, globalHandler] of this.globalHandlers) {
        if (globalEvent === eventType && globalHandler !== handler) {
          globalHandler(roomId, senderId, message, eventType);
        }
      }
    };
  }
}

export class WebRTCConnection {
  constructor(roomName, options = {}) {
    const { peerId, debug } = options;

    this.roomName = roomName;
    this.peerId = peerId || 'peer-' + Math.random().toString(36).substr(2, 9);
    this.debug = debug || false;
    this.pc = null;
    this.dataChannel = null;
    this.remoteDescriptionSet = false;
    this._remotePeerId = null;  // Store the remote peer's ID
    this.activePeers = new Set(); // Track all active peers
    
    // Socket.io-like event system
    this.onMessage = () => {};
    this.onOpen = () => {};
    this.onClose = () => {};
    this.onError = () => {};
    this.onStatusChange = () => {};
    this.onPeerJoined = () => {}; // New peer joins room
    this.onPeerLeft = () => {}; // Peer leaves room
    this.onRoomUpdate = () => {}; // Room state changes
    
    // Room state management
    this.roomState = {
      peers: new Map(), // peerId -> {id, joinTime, lastSeen}
      isHost: false,
      hostId: null
    };

    // Default TURN servers
    this.defaultTurnServers = [
      {
        urls: "turn:openrelay.metered.ca:80",
        username: "openrelayproject",
        credential: "openrelayproject"
      },
      {
        urls: "turn:openrelay.metered.ca:443",
        username: "openrelayproject",
        credential: "openrelayproject"
      },
      {
        urls: "turn:openrelay.metered.ca:3478",
        username: "openrelayproject",
        credential: "openrelayproject"
      }
    ];

    // Add basic reconnection properties
    this.maxReconnectAttempts = options.maxReconnectAttempts || 3;
    this.reconnectDelay = options.reconnectDelay || 2000;
    this.reconnectAttempts = 0;
    this.isReconnecting = false;
  }

  _log(...args) {
    if (this.debug) {
      console.log(...args);
    }
  }

  async connect() {
    this.pc = new RTCPeerConnection({
      iceServers: [
        { urls: 'stun:stun.l.google.com:19302' },
        ...this.defaultTurnServers // Include TURN servers
      ]
    });

    this.pc.onicecandidate = async (event) => {
      if (event.candidate) {
        this._log("[ICE] New ICE candidate:", event.candidate.candidate);
        try {
          const response = await fetch("/candidate", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              room: this.roomName,
              peer_id: this.peerId,
              candidate: {
                candidate: event.candidate.candidate,
                sdpMid: event.candidate.sdpMid,
                sdpMLineIndex: event.candidate.sdpMLineIndex,
                // Include other fields if necessary for the backend
                foundation: event.candidate.foundation,
                component: event.candidate.component,
                priority: event.candidate.priority,
                protocol: event.candidate.protocol,
                type: event.candidate.type,
                address: event.candidate.address,
                port: event.candidate.port
              }
            })
          });
          if (!response.ok) {
            const errorText = await response.text();
            console.error("[ICE] Failed to send candidate:", response.status, errorText);
          }
        } catch (error) {
          console.error("[ICE] Error sending candidate:", error);
        }
      } else {
        this._log("[ICE] ICE gathering complete");
      }
    };

    this.pc.oniceconnectionstatechange = () => {
      this._log("[ICE] Connection state:", this.pc.iceConnectionState);
      this.onStatusChange(`ICE: ${this.pc.iceConnectionState}`);
      if (this.pc.iceConnectionState === 'failed' && this.pc.restartIce) {
            this.pc.restartIce();
      }
    };

    this.pc.onconnectionstatechange = () => {
      this._log("[CONNECTION] State:", this.pc.connectionState);
      this.onStatusChange(`Connection: ${this.pc.connectionState}`);
      
      if (this.pc.connectionState === 'failed' || this.pc.connectionState === 'closed') {
        this.onClose();
      }
    };

    this.pc.onsignalingstatechange = () => {
      this._log("[SDP] Signaling state:", this.pc.signalingState);
    };

    this.dataChannel = this.pc.createDataChannel("chat", {
      ordered: true,
      maxRetransmits: 3
    });

    this.dataChannel.onopen = () => {
      this._log("[CHANNEL] Data channel opened");
      if (this.dataChannel.readyState === "open") {
        this._announceJoin();
        this.onOpen();
      }
    };

    this.dataChannel.onclose = () => {
      this._log("[CHANNEL] Data channel closed");
      this._announceDeparture();
      this._resetRoomState();
      this.onClose();
    };

    this.dataChannel.onmessage = (event) => {
      this._handleMessage(event.data);
    };

    this.dataChannel.onerror = (error) => {
      console.error("[CHANNEL] Data channel error:", error);
      this.onError(error);
    };

    this.pc.ondatachannel = (event) => {
      this._log("[CHANNEL] Received remote data channel");
      const remoteChannel = event.channel;
      remoteChannel.onmessage = (event) => {
        this._handleMessage(event.data);
      };
      remoteChannel.onopen = () => {
        this._log("[CHANNEL] Remote data channel opened");
        this.onOpen();
      };
    };

    try {
      const offer = await this.pc.createOffer();
      await this.pc.setLocalDescription(offer);

      const response = await fetch("/offer", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          room: this.roomName,
          peer_id: this.peerId,
          offer: {
            sdp: offer.sdp,
            type: offer.type
          }
        })
      });

      if (!response.ok) {
        throw new Error(`Server error: ${response.status}`);
      }

      const data = await response.json();
      const answer = new RTCSessionDescription(data.answer);
      await this.pc.setRemoteDescription(answer);
      this.remoteDescriptionSet = true;
      
      // Set remote peer ID from the answer
      if (data.peer_id && data.peer_id !== this.peerId) {
        this._remotePeerId = data.peer_id;
        this._log(`[PEER] Connected to peer: ${data.peer_id}`);
        this.onStatusChange("Connected to peer: " + data.peer_id);
      } else {
        this.onStatusChange("Waiting for connection...");
      }

    } catch (error) {
      this.onError(error);
      throw error;
    }
  }

  async handleDisconnection() {
    if (this.isReconnecting) return;
    this.isReconnecting = true;

    while (this.reconnectAttempts < this.maxReconnectAttempts) {
      this._log(`[RECONNECT] Attempt ${this.reconnectAttempts + 1}/${this.maxReconnectAttempts}`);
      this.onStatusChange(`Reconnecting: Attempt ${this.reconnectAttempts + 1}`);

      try {
        await this.closeConnection();
        await new Promise(resolve => setTimeout(resolve, this.reconnectDelay));
        await this.connect();
        
        if (this.isConnected()) {
          this._log("[RECONNECT] Successfully reconnected");
          this.reconnectAttempts = 0;
          this.isReconnecting = false;
          return true;
        }
      } catch (error) {
        this._log("[RECONNECT] Failed attempt:", error);
      }

      this.reconnectAttempts++;
      await new Promise(resolve => setTimeout(resolve, this.reconnectDelay));
    }

    this.isReconnecting = false;
    this.onError(new Error("Failed to reconnect after maximum attempts"));
    return false;
  }

  sendMessage(message) {
    if (this.dataChannel && this.dataChannel.readyState === "open") {
      const payload = JSON.stringify({
        peer_id: this.peerId,
        message: message
      });
      this.dataChannel.send(payload);
      this._log(`[SEND] Message sent: ${message}`);
    } else {
      console.warn("[SEND] Data channel not open. State:", this.dataChannel?.readyState);
      this.onError(new Error('Data channel not available for sending'));
    }
  }

  async closeConnection() {
    this._announceDeparture();
    
    if (this.pc) {
      await fetch("/leave", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
          room: this.roomName, 
          peer_id: this.peerId 
        })
      });
      this.pc.close();
      this.pc = null;
      this.dataChannel = null;
      this.remoteDescriptionSet = false;
      this._resetRoomState();
      this.onClose();
    }
  }

  isConnected() {
    return this.pc && 
           this.pc.connectionState === 'connected' && 
           this.dataChannel && 
           this.dataChannel.readyState === 'open';
  }
  
  // Add connection status details
  getConnectionStatus() {
    return {
      peerConnection: this.pc?.connectionState || 'not-created',
      iceConnection: this.pc?.iceConnectionState || 'not-created',
      dataChannel: this.dataChannel?.readyState || 'not-created',
      isFullyConnected: this.isConnected()
    };
  }

  // === SOCKET.IO-LIKE API ===
  
  emit(event, data) {
    if (!event) {
      console.warn('[EMIT] Event name is required');
      return false;
    }
    this._sendSystemMessage('EVENT', { event, data });
    return true;
  }
  
  broadcast(event, data) {
    if (!event) {
      console.warn('[BROADCAST] Event name is required');
      return false;
    }
    this._sendSystemMessage('BROADCAST', { event, data });
    return true;
  }
  
  // Add method to send raw JSON (for server broadcasts)
  sendRawJSON(jsonObject) {
    if (this.dataChannel && this.dataChannel.readyState === "open") {
      const payload = JSON.stringify(jsonObject);
      this.dataChannel.send(payload);
      this._log(`[SEND] Raw JSON sent:`, jsonObject);
      return true;
    } else {
      console.warn("[SEND] Data channel not open for raw JSON");
      return false;
    }
  }
  
  getRoomPeers() {
    return Array.from(this.roomState.peers.values());
  }
  
  getPeerCount() {
    return this.roomState.peers.size;
  }
  
  isRoomHost() {
    return this.roomState.isHost;
  }
  
  // === INTERNAL METHODS ===
  
  _handleMessage(rawData) {
    this._log(`[CHANNEL] Received: ${rawData}`);
    
    try {
      const data = JSON.parse(rawData);
      
      if (data.type === 'SYSTEM') {
        this._handleSystemMessage(data);
      } else if (data.peer_id && data.message !== undefined) {
        // Standard peer message format {peer_id: "1", message: "hello"}
        this._updatePeerActivity(data.peer_id);
        this.onMessage(data.peer_id, data.message);
      } else if (data.event) {
        // Custom event format {event: "chat-list-update", ...}
        this.onMessage('server', data, data.event);
      } else {
        // Raw JSON object - pass as message
        this.onMessage('unknown', data);
      }
    } catch (error) {
      // Not JSON - treat as plain text message
      this.onMessage('unknown', rawData);
    }
  }
  
  _handleSystemMessage(data) {
    const { action, payload, peer_id } = data;
    
    switch (action) {
      case 'PEER_JOIN':
        this._handlePeerJoin(peer_id, payload);
        break;
      case 'PEER_LEAVE':
        this._handlePeerLeave(peer_id);
        break;
      case 'ROOM_STATE':
        this._handleRoomState(payload);
        break;
      case 'HOST_CHANGE':
        this._handleHostChange(payload);
        break;
      case 'EVENT':
        this.onMessage(peer_id, payload.data, payload.event);
        break;
      case 'BROADCAST':
        this.onMessage(peer_id, payload.data, payload.event);
        break;

    }
  }
  
  _handlePeerJoin(peerId, peerInfo) {
    if (peerId === this.peerId) return;
    
    const peer = {
      id: peerId,
      joinTime: Date.now(),
      lastSeen: Date.now(),
      ...peerInfo
    };
    
    this.roomState.peers.set(peerId, peer);
    this.activePeers.add(peerId);
    
    this._log(`[PEER] ${peerId} joined room`);
    this.onPeerJoined(peer);
    this.onRoomUpdate(this.getRoomPeers());
    
    // Send current room state to new peer
    this._sendRoomState(peerId);
  }
  
  _handlePeerLeave(peerId) {
    const peer = this.roomState.peers.get(peerId);
    if (peer) {
      this.roomState.peers.delete(peerId);
      this.activePeers.delete(peerId);
      
      this._log(`[PEER] ${peerId} left room`);
      this.onPeerLeft(peer);
      this.onRoomUpdate(this.getRoomPeers());
      
      // Handle host change if needed
      if (peerId === this.roomState.hostId) {
        this._electNewHost();
      }
    }
  }
  
  _handleRoomState(roomState) {
    // Sync room state from another peer
    roomState.peers.forEach(peer => {
      if (peer.id !== this.peerId) {
        this.roomState.peers.set(peer.id, peer);
        this.activePeers.add(peer.id);
      }
    });
    
    this.onRoomUpdate(this.getRoomPeers());
  }
  
  _handleHostChange(hostId) {
    this.roomState.hostId = hostId;
    this.roomState.isHost = (hostId === this.peerId);
    this._log(`[HOST] New host: ${hostId}`);
  }
  
  _updatePeerActivity(peerId) {
    const peer = this.roomState.peers.get(peerId);
    if (peer) {
      peer.lastSeen = Date.now();
    }
  }
  
  _announceJoin() {
    const peerInfo = {
      userAgent: navigator.userAgent,
      timestamp: Date.now()
    };
    
    this._sendSystemMessage('PEER_JOIN', peerInfo);
    
    // Add self to room
    this.roomState.peers.set(this.peerId, {
      id: this.peerId,
      joinTime: Date.now(),
      lastSeen: Date.now(),
      ...peerInfo
    });
    
    // Become host if first peer
    if (this.roomState.peers.size === 1) {
      this.roomState.isHost = true;
      this.roomState.hostId = this.peerId;
    }
  }
  
  _announceDeparture() {
    if (this.dataChannel && this.dataChannel.readyState === 'open') {
      this._sendSystemMessage('PEER_LEAVE', {});
    }
  }
  
  _sendRoomState(targetPeerId) {
    const roomState = {
      peers: this.getRoomPeers(),
      hostId: this.roomState.hostId
    };
    
    this._sendSystemMessage('ROOM_STATE', roomState, targetPeerId);
  }
  
  _electNewHost() {
    const peers = this.getRoomPeers();
    if (peers.length > 0) {
      // Elect oldest peer as new host
      const newHost = peers.reduce((oldest, peer) => 
        peer.joinTime < oldest.joinTime ? peer : oldest
      );
      
      this.roomState.hostId = newHost.id;
      this.roomState.isHost = (newHost.id === this.peerId);
      
      this._sendSystemMessage('HOST_CHANGE', newHost.id);
    }
  }
  
  _sendSystemMessage(action, payload, targetPeerId = null) {
    if (this.dataChannel && this.dataChannel.readyState === 'open') {
      const message = {
        type: 'SYSTEM',
        action,
        payload,
        peer_id: this.peerId,
        target: targetPeerId,
        timestamp: Date.now()
      };
      
      try {
        this.dataChannel.send(JSON.stringify(message));
        this._log(`[SYSTEM] Sent ${action}:`, payload);
      } catch (error) {
        console.error(`[SYSTEM] Failed to send ${action}:`, error);
        this.onError(error);
      }
    } else {
      console.warn(`[SYSTEM] Cannot send ${action} - data channel not ready`);
    }
  }
  
  _resetRoomState() {
    this._remotePeerId = null;
    this.activePeers.clear();
    this.roomState.peers.clear();
    this.roomState.isHost = false;
    this.roomState.hostId = null;
  }
}
