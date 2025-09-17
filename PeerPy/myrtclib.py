import asyncio
from aiortc import RTCPeerConnection, RTCSessionDescription, RTCConfiguration, RTCIceServer, RTCIceCandidate
import logging
import json

logger = logging.getLogger("myrtc")

class Peer:
    def __init__(self, peer_id: str, pc: RTCPeerConnection):
        self.peer_id = peer_id
        self.pc = pc
        self.channel = None
        self.room = None

    def set_channel(self, channel):
        self.channel = channel

        @channel.on("message")
        def on_message(message):
            logger.info(f"Data received from peer {self.peer_id}: {message}")
            # Call the room's message callback if available
            if self.room and self.room.on_message_callback:
                # Use asyncio.create_task to avoid blocking
                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(self.room.on_message_callback(self.room.name, self.peer_id, message))
                except RuntimeError:
                    logger.error("No running event loop for room message callback")

            # Broadcast to other peers in the room (existing logic)
            if self.room:
                # Use asyncio.create_task to avoid blocking
                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(self.room.broadcast(self.peer_id, message))
                except RuntimeError:
                    logger.error("No running event loop for broadcasting message")

class Room:
    def __init__(self, name: str, turn_servers: list = None, on_message_callback=None):
        self.name = name
        self.peers = {}  # peer_id -> Peer
        self.pending_candidates = {}  # peer_id -> list of candidates
        # Create lock in the current event loop
        self.lock = asyncio.Lock()
        self.turn_servers = turn_servers if turn_servers is not None else []
        self.on_message_callback = on_message_callback
        logger.info(f"Created room: {name} with TURN servers: {self.turn_servers}")

    async def add_peer(self, peer_id: str, offer: dict) -> dict:
        """
        Create a peer connection for a new peer and return the SDP answer.
        """
        logger.info(f"Adding peer {peer_id} to room {self.name}")

        # Create RTCPeerConnection with STUN/TURN servers
        ice_servers = [RTCIceServer(urls="stun:stun.l.google.com:19302")]
        if self.turn_servers:
            for turn_server in self.turn_servers:
                ice_servers.append(RTCIceServer(
                    urls=turn_server["urls"],
                    username=turn_server.get("username"),
                    credential=turn_server.get("credential")
                ))

        config = RTCConfiguration(ice_servers)
        pc = RTCPeerConnection(configuration=config)

        peer = Peer(peer_id, pc)
        peer.room = self

        # Monitor ICE connection state
        @pc.on("iceconnectionstatechange")
        async def on_ice_state_change():
            logger.info(f"Peer {peer_id} ICE connection state: {pc.iceConnectionState}")
            if pc.iceConnectionState in ("failed", "closed", "disconnected"):
                logger.warning(f"Peer {peer_id} ICE connection failed/closed")
                # Schedule removal in the event loop to avoid lock issues
                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(self._safe_remove_peer(peer_id))
                except RuntimeError:
                    logger.error("No running event loop for peer removal")

        # Handle incoming data channel from browser
        @pc.on("datachannel")
        def on_datachannel(channel):
            logger.info(f"Received data channel from peer {peer_id}")
            peer.set_channel(channel)

        try:
            # Set the remote description (offer from browser)
            remote_desc = RTCSessionDescription(
                sdp=offer["sdp"],
                type=offer["type"]
            )
            await pc.setRemoteDescription(remote_desc)
            logger.info(f"Set remote description for peer {peer_id}")

            # Create and set local description (answer)
            answer = await pc.createAnswer()
            await pc.setLocalDescription(answer)
            logger.info(f"Created answer for peer {peer_id}")

            # Add peer to room and process pending ICE candidates
            async with self.lock:
                self.peers[peer_id] = peer
                
                # Process any pending ICE candidates
                if peer_id in self.pending_candidates:
                    candidates = self.pending_candidates.pop(peer_id)
                    logger.info(f"Processing {len(candidates)} pending ICE candidates for peer {peer_id}")
                    
                    for candidate_data in candidates:
                        try:
                            candidate = self._create_ice_candidate(candidate_data)
                            await peer.pc.addIceCandidate(candidate)
                            logger.info(f"Added ICE candidate for peer {peer_id}")
                        except Exception as e:
                            logger.error(f"Failed to add ICE candidate for peer {peer_id}: {e}")

            logger.info(f"Peer {peer_id} successfully joined room {self.name}")
            
            return {
                "sdp": pc.localDescription.sdp,
                "type": pc.localDescription.type
            }

        except Exception as e:
            logger.error(f"Failed to add peer {peer_id}: {e}")
            try:
                await pc.close()
            except:
                pass
            raise

    def _create_ice_candidate(self, candidate_data: dict) -> RTCIceCandidate:
        """Create RTCIceCandidate from candidate data"""
        # The client sends the candidate as a dictionary with 'candidate', 'sdpMid', 'sdpMLineIndex'
        # aiortc's RTCIceCandidate expects these directly.
        return RTCIceCandidate(
            candidate=candidate_data.get("candidate"),
            sdpMid=candidate_data.get("sdpMid"),
            sdpMLineIndex=candidate_data.get("sdpMLineIndex")
        )

    async def add_ice_candidate(self, peer_id: str, candidate_data: dict):
        """
        Add an ICE candidate to a peer's connection.
        """
        logger.info(f"Processing ICE candidate for peer {peer_id}")
        logger.debug(f"Candidate data: {candidate_data}")
        
        async with self.lock:
            peer = self.peers.get(peer_id)
            
            if peer:
                try:
                    candidate = self._create_ice_candidate(candidate_data)
                    await peer.pc.addIceCandidate(candidate)
                    logger.info(f"Successfully added ICE candidate for peer {peer_id}")
                except Exception as e:
                    logger.error(f"Failed to add ICE candidate for peer {peer_id}: {e}")
                    # Log the candidate data for debugging
                    logger.error(f"Problematic candidate data: {candidate_data}")
            else:
                # Store candidate for when peer joins
                if peer_id not in self.pending_candidates:
                    self.pending_candidates[peer_id] = []
                self.pending_candidates[peer_id].append(candidate_data)
                logger.info(f"Stored pending ICE candidate for peer {peer_id} (total pending: {len(self.pending_candidates[peer_id])})")

    async def broadcast(self, sender_id: str, message: str):
        """
        Send a message from one peer to all others in the room.
        """
        logger.info(f"Broadcasting data from {sender_id}: {message}")
        
        async with self.lock:
            recipients = []
            for pid, peer in self.peers.items():
                if pid != sender_id and peer.channel:
                    recipients.append((pid, peer))
        
        # Send to all recipients (outside the lock to avoid blocking)
        for pid, peer in recipients:
            try:
                if peer.channel and hasattr(peer.channel, 'send'):
                    peer.channel.send(message)
                    logger.info(f"Data sent to peer {pid}")
            except Exception as e:
                logger.warning(f"Failed to send message to peer {pid}: {e}")

    async def _safe_remove_peer(self, peer_id: str):
        """
        Safely remove a peer (can be called from event handlers)
        """
        try:
            await self.remove_peer(peer_id)
        except Exception as e:
            logger.error(f"Error in safe peer removal for {peer_id}: {e}")

    async def remove_peer(self, peer_id: str):
        """
        Remove a peer from the room and close their connection.
        """
        async with self.lock:
            peer = self.peers.pop(peer_id, None)
            
            if peer:
                try:
                    if peer.pc and peer.pc.connectionState != "closed":
                        await peer.pc.close()
                    logger.info(f"Peer {peer_id} removed from room {self.name}")
                except Exception as e:
                    logger.error(f"Error closing connection for peer {peer_id}: {e}")
            else:
                logger.warning(f"Attempted to remove non-existent peer {peer_id}")

    def get_peer_count(self) -> int:
        """Get the number of peers in the room."""
        return len(self.peers)