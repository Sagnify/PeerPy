import logging
import json

# Use the same logger as the rest of the library for consistency
logger = logging.getLogger("signaling-manager")

class Broadcaster:
    """
    A helper class to broadcast messages from the backend to all clients in a room.
    It uses the existing SignalingManager to access peers.
    """
    def __init__(self, signaling_manager):
        self.signaling_manager = signaling_manager
        logger.info("Broadcaster initialized.")

    def broadcast(self, room_name: str, message: str):
        """
        Broadcast a message to all peers in a given room.
        This method is synchronous and will run the broadcast in the background
        using the signaling manager's event loop.
        """
        # Find the room in the signaling manager's list of rooms
        room = self.signaling_manager.rooms.get(room_name)
        if not room:
            logger.warning(f"Broadcast failed: Room '{room_name}' not found.")
            return

        async def _process_broadcast():
            """The actual async function to send messages."""
            payload = json.dumps({
                "peer_id": "server",  # A special ID to indicate the message is from the server
                "message": message
            })
            
            peers_to_send = []
            # Safely get the list of peers to send to
            async with room.lock:
                for peer in room.peers.values():
                    # Check if the peer's data channel is open and ready
                    if peer.channel and peer.channel.readyState == "open":
                        peers_to_send.append(peer)
            
            if not peers_to_send:
                logger.info(f"No connected peers in room '{room_name}' to broadcast to.")
                return

            logger.info(f"Broadcasting message to {len(peers_to_send)} peers in room '{room_name}'.")
            
            # Send the message to each peer
            for peer in peers_to_send:
                try:
                    peer.channel.send(payload)
                except Exception as e:
                    logger.error(f"Failed to send broadcast to peer {peer.peer_id}: {e}")

        # Use the signaling manager to run the async broadcast function in its event loop
        self.signaling_manager.run_async(_process_broadcast())
