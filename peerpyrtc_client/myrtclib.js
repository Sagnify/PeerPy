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
    } else {
      console.warn("[SEND] Data channel not open.");
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
    return this.pc && this.pc.connectionState === 'connected';
  }

  // === SOCKET.IO-LIKE API ===
  
  emit(event, data) {
    this._sendSystemMessage('EVENT', { event, data });
  }
  
  broadcast(event, data) {
    this._sendSystemMessage('BROADCAST', { event, data });
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
      } else {
        // Regular user message
        this._updatePeerActivity(data.peer_id);
        this.onMessage(data.peer_id, data.message);
      }
    } catch (error) {
      console.error('[MESSAGE] Parse error:', error);
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
      
      this.dataChannel.send(JSON.stringify(message));
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
