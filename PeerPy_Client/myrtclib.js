export class WebRTCConnection {
  constructor(roomName, peerId) {
    this.roomName = roomName;
    this.peerId = peerId;
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

  async connect() {
    this.pc = new RTCPeerConnection({
      iceServers: [
        { urls: 'stun:stun.l.google.com:19302' },
        ...this.defaultTurnServers // Include TURN servers
      ]
    });

    this.pc.onicecandidate = async (event) => {
      if (event.candidate) {
        console.log("[ICE] New ICE candidate:", event.candidate.candidate);
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
        console.log("[ICE] ICE gathering complete");
      }
    };

    this.pc.oniceconnectionstatechange = () => {
      console.log("[ICE] Connection state:", this.pc.iceConnectionState);
      this.onStatusChange(`ICE: ${this.pc.iceConnectionState}`);
      if (this.pc.iceConnectionState === 'failed') {
        if (this.pc.restartIce) {
          this.pc.restartIce();
        }
      }
    };

    this.pc.onconnectionstatechange = () => {
      console.log("[CONNECTION] State:", this.pc.connectionState);
      this.onStatusChange(`Connection: ${this.pc.connectionState}`);
      if (this.pc.connectionState === 'connected') {
        this.onOpen();
      } else if (this.pc.connectionState === 'failed' || this.pc.connectionState === 'closed') {
        this.onClose();
      }
    };

    this.pc.onsignalingstatechange = () => {
      console.log("[SDP] Signaling state:", this.pc.signalingState);
    };

    this.dataChannel = this.pc.createDataChannel("chat", {
      ordered: true,
      maxRetransmits: 3
    });

    this.dataChannel.onopen = () => {
      console.log("[CHANNEL] Data channel opened");
      this.onOpen();
    };

    this.dataChannel.onclose = () => {
      console.log("[CHANNEL] Data channel closed");
      this.onClose();
    };

    this.dataChannel.onmessage = (event) => {
      console.log(`[CHANNEL] Received: ${event.data}`);
      this.onMessage(event.data);
    };

    this.dataChannel.onerror = (error) => {
      console.error("[CHANNEL] Data channel error:", error);
      this.onError(error);
    };

    this.pc.ondatachannel = (event) => {
      console.log("[CHANNEL] Received remote data channel");
      const remoteChannel = event.channel;
      remoteChannel.onmessage = (event) => {
        console.log(`[CHANNEL] Remote message: ${event.data}`);
        this.onMessage(event.data);
      };
      remoteChannel.onopen = () => {
        console.log("[CHANNEL] Remote data channel opened");
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
      this.dataChannel.send(message);
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