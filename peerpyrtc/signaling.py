import asyncio
import logging
import threading
import time
from .peerpyrtc import Room

# Get the loggers for the library
myrtc_logger = logging.getLogger("myrtc")
signaling_logger = logging.getLogger("signaling-manager")

class SignalingManager:
    def __init__(self, debug=False):
        # Configure logging based on the debug flag
        if debug:
            log_level = logging.INFO
        else:
            log_level = logging.WARNING

        myrtc_logger.setLevel(log_level)
        signaling_logger.setLevel(log_level)

        # Add a handler for the root logger if none is configured
        # This ensures that logs are displayed by default
        if not logging.getLogger().hasHandlers():
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logging.getLogger().addHandler(handler)
            logging.getLogger().setLevel(log_level)

        self.rooms = {}
        self._async_loop = None
        self._loop_thread = None
        self._start_event_loop()
        # Define default TURN servers here
        self.default_turn_servers = [
            {
                "urls": "turn:openrelay.metered.ca:80",
                "username": "openrelayproject",
                "credential": "openrelayproject"
            },
            {
                "urls": "turn:openrelay.metered.ca:443",
                "username": "openrelayproject",
                "credential": "openrelayproject"
            },
            {
                "urls": "turn:openrelay.metered.ca:3478",
                "username": "openrelayproject",
                "credential": "openrelayproject"
            }
        ]
        self._message_handler = self._default_message_logger # Set default handler
        self._peer_joined_handler = None
        self._peer_left_handler = None

    def _start_event_loop(self):
        def run_loop():
            self._async_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._async_loop)
            self._async_loop.run_forever()

        self._loop_thread = threading.Thread(target=run_loop, daemon=True)
        self._loop_thread.start()
        signaling_logger.info("Asyncio event loop started in a separate thread.")

    def get_event_loop(self):
        """Get the asyncio loop running in the background thread"""
        while self._async_loop is None:
            time.sleep(0.1) # Wait for the loop to be initialized
        return self._async_loop

    async def _default_message_logger(self, room_name: str, sender_id: str, message: str):
        """Default message handler that logs messages."""
        signaling_logger.info(f"[DEFAULT_BACKEND_MESSAGE] Room: {room_name}, Sender: {sender_id}, Message: {message}")

    def set_message_handler(self, handler):
        """Set a handler function to be called when a message is received by any peer."""
        if not asyncio.iscoroutinefunction(handler):
            signaling_logger.warning("Provided message handler is not an async function. It might block the event loop.")
        self._message_handler = handler

    def message_handler(self, func):
        """
        Decorator to register a function as the message handler.
        The decorated function must be an async function and accept
        (room_name: str, sender_id: str, message: str) as arguments.
        """
        self.set_message_handler(func)
        return func # Return the original function so it can still be called if needed
    
    def peer_joined_handler(self, func):
        """
        Decorator to register a function as the peer joined handler.
        The decorated function must be an async function and accept
        (room_name: str, peer_id: str, peer_info: dict) as arguments.
        """
        self._peer_joined_handler = func
        return func
    
    def peer_left_handler(self, func):
        """
        Decorator to register a function as the peer left handler.
        The decorated function must be an async function and accept
        (room_name: str, peer_id: str, peer_info: dict) as arguments.
        """
        self._peer_left_handler = func
        return func

    async def _handle_room_message(self, room_name: str, sender_id: str, message: str):
        """Internal handler for messages received by a room's peer."""
        if self._message_handler:
            # Run the user-defined message handler in the background event loop
            try:
                await self._message_handler(room_name, sender_id, message)
            except Exception as e:
                signaling_logger.error(f"Error in user-defined message handler: {e}")
        else:
            signaling_logger.debug(f"No message handler set in SignalingManager for room {room_name}, peer {sender_id}: {message}")
    
    async def _handle_peer_joined(self, room_name: str, peer_id: str, peer_info: dict):
        """Internal handler for peer joined events."""
        if self._peer_joined_handler:
            try:
                await self._peer_joined_handler(room_name, peer_id, peer_info)
            except Exception as e:
                signaling_logger.error(f"Error in peer joined handler: {e}")
    
    async def _handle_peer_left(self, room_name: str, peer_id: str, peer_info: dict):
        """Internal handler for peer left events."""
        if self._peer_left_handler:
            try:
                await self._peer_left_handler(room_name, peer_id, peer_info)
            except Exception as e:
                signaling_logger.error(f"Error in peer left handler: {e}")

    def get_room(self, room_name: str) -> Room:
        """Get or create a room"""
        if room_name not in self.rooms:
            # Pass TURN servers to the Room constructor
            room = Room(
                room_name,
                turn_servers=self.default_turn_servers,
                on_message_callback=self._handle_room_message
            )
            room.on_peer_joined = self._handle_peer_joined
            room.on_peer_left = self._handle_peer_left
            self.rooms[room_name] = room
            signaling_logger.info(f"Created new room: {room_name}")
        return self.rooms[room_name]

    def run_async(self, coro):
        """Run an async coroutine from sync context using the dedicated event loop"""
        loop = self.get_event_loop()
        future = asyncio.run_coroutine_threadsafe(coro, loop)
        return future.result()

    def offer(self, room_name: str, peer_id: str, offer: dict) -> dict:
        room = self.get_room(room_name)
        async def _process():
            return await room.add_peer(peer_id, offer)
        return self.run_async(_process())

    def candidate(self, room_name: str, peer_id: str, candidate: dict):
        room = self.get_room(room_name)
        async def _process():
            await room.add_ice_candidate(peer_id, candidate)
        self.run_async(_process())

    def leave(self, room_name: str, peer_id: str):
        if room_name in self.rooms:
            room = self.rooms[room_name]
            async def _process():
                await room.remove_peer(peer_id)
            self.run_async(_process())
            if room.get_peer_count() == 0:
                del self.rooms[room_name]
                signaling_logger.info(f"[CLEANUP] Removed empty room: {room_name}")

    def rooms_info(self) -> dict:
        room_info = {}
        for name, room in self.rooms.items():
            room_info[name] = {
                "peer_count": room.get_peer_count(),
                "peers": room.get_peer_list(),
                "host_id": room.get_host_id()
            }
        return room_info
    
    def get_room_peers(self, room_name: str) -> list:
        """Get list of peers in a specific room"""
        if room_name in self.rooms:
            return self.rooms[room_name].get_peer_list()
        return []
def rooms_info(self) -> dict:
        room_info = {}
        for name, room in self.rooms.items():
            room_info[name] = {
                "peer_count": room.get_peer_count(),
                "peers": list(room.peers.keys())
            }
        return room_info
