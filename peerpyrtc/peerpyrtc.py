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

            try:
                data = json.loads(message)
                
                # Handle system messages
                if data.get('type') == 'SYSTEM':
                    if self.room:
                        try:
                            loop = asyncio.get_running_loop()
                            loop.create_task(self.room.handle_system_message(self.peer_id, data))
                        except RuntimeError:
                            logger.error("No running event loop for system message")
                else:
                    # Regular message
                    actual_message = data.get('message', message)
                    
                    # Call the room's message callback
                    if self.room and self.room.on_message_callback:
                        try:
                            loop = asyncio.get_running_loop()
                            loop.create_task(self.room.on_message_callback(self.room.name, self.peer_id, actual_message))
                        except RuntimeError:
                            logger.error("No running event loop for room message callback")
            except json.JSONDecodeError:
                actual_message = message
                if self.room and self.room.on_message_callback:
                    try:
                        loop = asyncio.get_running_loop()
                        loop.create_task(self.room.on_message_callback(self.room.name, self.peer_id, actual_message))
                    except RuntimeError:
                        logger.error("No running event loop for room message callback")

            # Always broadcast to other peers
            if self.room:
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
        self.peer_metadata = {}  # peer_id -> {joinTime, userAgent, etc}
        self.host_id = None
        # Create lock in the current event loop
        self.lock = asyncio.Lock()
        self.turn_servers = turn_servers if turn_servers is not None else []
        self.on_message_callback = on_message_callback
        self.on_peer_joined = None
        self.on_peer_left = None
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

    async def handle_system_message(self, sender_id: str, data: dict):
        """Handle system messages for peer management"""
        action = data.get('action')
        payload = data.get('payload', {})
        
        if action == 'PEER_JOIN':
            await self._handle_peer_join(sender_id, payload)
        elif action == 'PEER_LEAVE':
            await self._handle_peer_leave(sender_id)
        elif action == 'HOST_CHANGE':
            self.host_id = payload
            logger.info(f"Host changed to {payload} in room {self.name}")
    
    async def _handle_peer_join(self, peer_id: str, peer_info: dict):
        """Handle peer join event"""
        async with self.lock:
            self.peer_metadata[peer_id] = {
                'joinTime': peer_info.get('timestamp', asyncio.get_event_loop().time()),
                'userAgent': peer_info.get('userAgent', 'Unknown'),
                'lastSeen': asyncio.get_event_loop().time()
            }
            
            # Set as host if first peer
            if not self.host_id:
                self.host_id = peer_id
                logger.info(f"Peer {peer_id} became host of room {self.name}")
        
        # Call callback if set
        if self.on_peer_joined:
            try:
                await self.on_peer_joined(self.name, peer_id, self.peer_metadata[peer_id])
            except Exception as e:
                logger.error(f"Error in peer joined callback: {e}")
        
        logger.info(f"Peer {peer_id} joined room {self.name}")
    
    async def _handle_peer_leave(self, peer_id: str):
        """Handle peer leave event"""
        peer_info = None
        async with self.lock:
            peer_info = self.peer_metadata.pop(peer_id, None)
            
            # Elect new host if needed
            if self.host_id == peer_id and self.peer_metadata:
                # Find oldest peer
                oldest_peer = min(self.peer_metadata.items(), 
                                key=lambda x: x[1]['joinTime'])
                self.host_id = oldest_peer[0]
                logger.info(f"New host elected: {self.host_id} in room {self.name}")
            elif not self.peer_metadata:
                self.host_id = None
        
        # Call callback if set
        if self.on_peer_left and peer_info:
            try:
                await self.on_peer_left(self.name, peer_id, peer_info)
            except Exception as e:
                logger.error(f"Error in peer left callback: {e}")
        
        logger.info(f"Peer {peer_id} left room {self.name}")
    
    def get_peer_count(self) -> int:
        """Get the number of peers in the room."""
        return len(self.peers)
    
    def get_peer_list(self) -> list:
        """Get list of all peers with metadata"""
        return [
            {
                'id': peer_id,
                'isHost': peer_id == self.host_id,
                **metadata
            }
            for peer_id, metadata in self.peer_metadata.items()
        ]
    
    def get_host_id(self) -> str:
        """Get current host peer ID"""
        return self.host_id