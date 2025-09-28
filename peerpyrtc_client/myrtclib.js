export class WebRTCConnection {
  constructor(roomName, options = {}) {
    const { peerId, debug } = options;

    this.roomName = roomName;
    this.peerId = peerId || 'peer-' + Math.random().toString(36).substr(2, 9);
    this.debug = debug || false;
    this.pc = null;
    this.dataChannel = null;
    this.remoteDescriptionSet = false;

    // Callbacks for application-specific logic
    this.onMessage = () => {};
    this.onOpen = () => {};
    this.onClose = () => {};
    this.onError = () => {};
    this.onStatusChange = () => {};

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
      if (this.pc.iceConnectionState === 'failed') {
        if (this.pc.restartIce) {
          this.pc.restartIce();
        }
      }
    };

    this.pc.onconnectionstatechange = () => {
      this._log("[CONNECTION] State:", this.pc.connectionState);
      this.onStatusChange(`Connection: ${this.pc.connectionState}`);
      if (this.pc.connectionState === 'connected') {
        this.onOpen();
      } else if (this.pc.connectionState === 'failed' || this.pc.connectionState === 'closed') {
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
      this.onOpen();
    };

    this.dataChannel.onclose = () => {
      this._log("[CHANNEL] Data channel closed");
      this.onClose();
    };

    this.dataChannel.onmessage = (event) => {
      this._log(`[CHANNEL] Received: ${event.data}`);
      const data = JSON.parse(event.data);
      this.onMessage(data.peer_id, data.message);
    };

    this.dataChannel.onerror = (error) => {
      console.error("[CHANNEL] Data channel error:", error);
      this.onError(error);
    };

    this.pc.ondatachannel = (event) => {
      this._log("[CHANNEL] Received remote data channel");
      const remoteChannel = event.channel;
      remoteChannel.onmessage = (event) => {
        this._log(`[CHANNEL] Remote message: ${event.data}`);
        const data = JSON.parse(event.data);
        this.onMessage(data.peer_id, data.message);
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
      this.onStatusChange("Waiting for connection...");

    } catch (error) {
      this.onError(error);
      throw error;
    }
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
      this.onClose();
    }
  }

  isConnected() {
    return this.pc && this.pc.connectionState === 'connected';
  }
}
