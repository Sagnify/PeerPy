# WebRTC DataChannel Libraries

This repository provides a set of modular libraries for building WebRTC DataChannel applications, separating core WebRTC logic from signaling and frontend concerns. These libraries are designed to be easily integrated into your own projects, with the included chat application serving as a practical example of their usage.

## Features

-   **Core WebRTC Abstraction:** Python classes for managing WebRTC peer connections and data channels.
-   **Signaling Server Utilities:** A Python class to streamline the creation of WebRTC signaling servers, framework-agnostic.
-   **Client-Side WebRTC Wrapper:** A JavaScript class to simplify WebRTC setup and interaction in the browser.
-   **Clear Separation of Concerns:** Backend and frontend logic are independently reusable.

## Installation

### Python
```
pip install peerpyrtc
```
### JavaScript
```
npm install peerpyrtc-client
```
## Getting Started (for Developers)

### Prerequisites

-   **Python:** 3.8+ (for backend libraries)
-   **`aiortc`:** Python library for WebRTC implementation.
-   **JavaScript Environment:** A modern web browser (for frontend library)



## Backend Libraries

### `PeerPy/signaling.py` (Signaling Manager)

This file provides a high-level, synchronous interface for managing WebRTC signaling operations. It is designed to be framework-agnostic and can be easily integrated into any Python web framework (e.g., Flask, FastAPI, Django).

#### `class SignalingManager`

Manages the global state of chat rooms and provides methods to handle common signaling requests. It handles the underlying asynchronous WebRTC operations and room management.

-   **`__init__(self)`:**
    -   Initializes the manager and sets up its internal mechanisms for handling WebRTC signaling.
-   **`offer(self, room_name: str, peer_id: str, offer: dict) -> dict`:**
    -   Processes an incoming WebRTC SDP offer from a client. It creates or retrieves a room, sets up a peer connection, and generates an SDP answer.
    -   **Returns:** The generated SDP answer as a dictionary.
-   **`candidate(self, room_name: str, peer_id: str, candidate: dict)`:**
    -   Processes an incoming ICE candidate from a client. It adds the candidate to the specified peer's connection.
-   **`leave(self, room_name: str, peer_id: str)`:**
    -   Handles a peer leaving a room. It closes the peer's connection and cleans up room resources if the room becomes empty.
-   **`rooms_info(self) -> dict`:**
    -   **Returns:** A dictionary containing information about all active rooms, including the number of peers and their IDs.

**Example Usage in a Flask Application (`app.py`):**

```python
import logging
from flask import Flask, request, jsonify, send_from_directory
from PeerPy.signaling import SignalingManager

# ... (logging setup)

app = Flask(__name__)
signaling_manager = SignalingManager()

@app.route("/offer", methods=["POST"])
def handle_offer():
    data = request.get_json()
    room_name = data.get("room")
    peer_id = data.get("peer_id")
    offer = data.get("offer")
    answer = signaling_manager.offer(room_name, peer_id, offer)
    return jsonify({"answer": answer})

@app.route("/candidate", methods=["POST"])
def handle_candidate():
    data = request.get_json()
    room_name = data.get("room")
    peer_id = data.get("peer_id")
    candidate = data.get("candidate")
    signaling_manager.candidate(room_name, peer_id, candidate)
    return jsonify({"status": "ok"})

# ... (other routes like /leave, /rooms, static file serving)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True, threaded=True)
```

### Backend Access to DataChannel Messages (for Persistence and Processing)

WebRTC DataChannels are fantastic for direct, real-time communication between clients. However, by default, your backend server is completely unaware of the messages exchanged over these channels. This means:

*   **No Message History:** If a user leaves and rejoins, their past messages are gone.
*   **No Backend Processing:** You can't store messages, analyze them, or integrate with other backend services.

To solve this, `PeerPy` provides a mechanism for your backend to receive a *copy* of every message sent over any DataChannel it manages. Think of it as a "message tap" – messages still flow directly between clients, but your server also gets a notification with the message content.

This enables powerful features for your application:

*   **Persistence:** Store messages in a database for chat history, offline messaging, or auditing.
*   **Analytics:** Analyze message patterns, user engagement, or content.
*   **Moderation:** Implement content filtering or user moderation.
*   **Integration:** Forward messages to other services (e.g., AI chatbots, notification systems).

#### How to Implement Backend Message Handling

The `SignalingManager` offers a straightforward way to register a function that will be called every time a DataChannel message is received by the backend.

**1. Default Behavior (Automatic Logging):**

If you don't explicitly register a handler, the `SignalingManager` will automatically log all incoming DataChannel messages to your server's console. This provides immediate visibility into the message flow without any extra code.

**2. Customizing with a Decorator (e.g., Saving to a Database):**

For custom logic, like saving messages to a database, you can use the `@signaling_manager.message_handler` decorator. This is a Pythonic way to register your asynchronous function directly.

Here's how you'd typically set this up in your Flask `app.py` (or similar backend file):

```python
# ... (your existing imports and Flask app setup) ...

from PeerPy import SignalingManager
import asyncio # Needed for async operations, especially for database calls

app = Flask(__name__)
signaling_manager = SignalingManager()

# --- Example Database Integration (Replace with your actual DB setup) ---
# In a real application, you would initialize your database client here.
# For demonstration, we'll use a simple mock database saver.
class MockDatabaseSaver:
    async def save_chat_message(self, room_name: str, sender_id: str, message: str):
        """Simulates saving a chat message to a database."""
        print(f"--- DB SAVE (MOCK) --- Room: '{room_name}', Sender: '{sender_id}', Message: '{message}'")
        await asyncio.sleep(0.1) # Simulate an asynchronous database write operation
        print("--- DB SAVE COMPLETE (MOCK) ---")

# Initialize your database saver (replace MockDatabaseSaver with your actual DB client)
my_db_saver = MockDatabaseSaver()

# --- Register Your Custom Message Handler ---
@signaling_manager.message_handler
async def handle_incoming_datachannel_message(room_name: str, sender_id: str, message: str):
    """
    This asynchronous function will be called by the SignalingManager
    for EVERY message sent over any DataChannel it manages.
    """
    logger.info(f"[BACKEND_MESSAGE_RECEIVED] Room: {room_name}, Sender: {sender_id}, Message: {message}")
    
    # This is where you implement your custom logic:
    await my_db_saver.save_chat_message(room_name, sender_id, message)
    # You could also:
    # - Perform sentiment analysis on 'message'
    # - Trigger a notification for 'sender_id'
    # - Update a real-time dashboard

# ... (your existing Flask routes and app.run) ...
```

By using the `@signaling_manager.message_handler` decorator, your backend function `handle_incoming_datachannel_message` will automatically receive `room_name`, `sender_id`, and the `message` content, allowing you to integrate powerful backend processing with your WebRTC DataChannels.

## Frontend Library

### `PeerPy_Client/myrtclib.js`

This file provides a client-side JavaScript class to simplify WebRTC operations in the browser, abstracting away the direct handling of `RTCPeerConnection` and `RTCDataChannel`.

#### `class WebRTCConnection`

Provides a convenient interface for client-side WebRTC operations, including connection setup, data channel management, and interaction with a signaling server.

-   **`constructor(roomName: string, peerId: string)`:**
    -   Initializes a new `WebRTCConnection` instance for a specific `roomName` and `peerId`.
    -   Sets up default empty callback functions for various events (`onMessage`, `onOpen`, `onClose`, `onError`, `onStatusChange`).
-   **`onMessage: (message: string) => void`:**
    -   Callback invoked when a message is received over the data channel.
-   **`onOpen: () => void`:**
    -   Callback invoked when the data channel successfully opens.
-   **`onClose: () => void`:**
    -   Callback invoked when the WebRTC connection or data channel closes.

-   **`onError: (error: Error) => void`:**
    -   Callback invoked when an error occurs during the WebRTC process.
-   **`onStatusChange: (status: string) => void`:**
    -   Callback invoked to provide updates on the connection status (e.g., ICE state, connection state).
-   **`async connect(): Promise<void>`:**
    -   Initiates the WebRTC connection process. This involves creating `RTCPeerConnection`, setting up event handlers, creating a data channel, generating an SDP offer, sending it to the signaling server (`/offer` endpoint), and processing the SDP answer.
-   **`sendMessage(message: string): void`:**
    -   Sends a `message` over the established data channel. Checks if the channel is open.
-   **`async closeConnection(): Promise<void>`:**
    -   Gracefully closes the WebRTC connection and notifies the signaling server (`/leave` endpoint).
-   **`isConnected(): boolean`:**
    -   Returns `true` if the WebRTC connection is currently established and the data channel is open, `false` otherwise.

**Example Usage in a JavaScript Application (`index.html`):**

```html
<!-- ... (HTML structure) -->

  <script type="module">
    import { WebRTCConnection } from '/PeerPy_Client/myrtclib.js';

    let rtcConnection;

    // ... (UI utility functions like log, updateStatus, generatePeerID)

    async function joinRoom() {
      const roomName = document.getElementById("room").value;
      const peerId = document.getElementById("peerId").value;
      // ... (input validation and UI updates)

      rtcConnection = new WebRTCConnection(roomName, peerId);

      rtcConnection.onMessage = (message) => { /* Update chat UI */ };
      rtcConnection.onOpen = () => { /* Update status, enable chat input */ };
      rtcConnection.onClose = () => { /* Update status, disable chat input */ };
      rtcConnection.onError = (error) => { /* Display error message */ };
      rtcConnection.onStatusChange = (status) => { /* Update status display */ };

      try {
        await rtcConnection.connect();
        // ... (success handling)
      } catch (error) {
        // ... (error handling)
      }
    }

    function sendMessage() {
      const messageInput = document.getElementById("message");
      const msg = messageInput.value.trim();
      if (msg && rtcConnection && rtcConnection.isConnected()) {
        rtcConnection.sendMessage(msg);
        // ... (update UI, clear input)
      } else {
        // ... (handle not connected)
      }
    }

    async function leaveRoom() {
      if (rtcConnection) {
        await rtcConnection.closeConnection();
        // ... (update UI)
      }
    }

    // ... (Event Listeners for buttons and input)
  </script>
```

## Example Application (`app.py` and `index.html`)

The `app.py` and `index.html` files in this repository demonstrate how to integrate and use the backend and frontend WebRTC libraries to build a functional chat application. They serve as a complete, runnable example.

### Running the Example Application

1.  **Start the Backend Signaling Server (Chat):**
    ```bash
    cd examples/chat && python app.py
    ```
    The server will typically run on `http://0.0.0.0:5000`.

2.  **Access the Frontend (Chat):**
    Open your web browser and navigate to `http://localhost:5000/`.
    
    To test peer-to-peer communication, open this URL in two different browser tabs or windows. Enter a common room name and unique Peer IDs for each tab, then click "Join Room" on both.

### Echo Application

The `app.py` and `index.html` files in the `examples/echo/` directory demonstrate a simple echo application using the WebRTC libraries.

### Running the Echo Application

1.  **Start the Backend Signaling Server (Echo):**
    ```bash
    cd examples/echo && python app.py
    ```
    The server will typically run on `http://0.0.0.0:5000`.

2.  **Access the Frontend (Echo):
    Open your web browser and navigate to `http://localhost:5000/`.

### Shared Whiteboard Application

The `app.py` and `index.html` files in the `examples/whiteboard/` directory demonstrate a real-time shared whiteboard application using the WebRTC libraries.

### Running the Shared Whiteboard Application

1.  **Start the Backend Signaling Server (Whiteboard):**
    ```bash
    cd examples/whiteboard && python app.py
    ```
    The server will typically run on `http://0.0.0.0:5000`.

2.  **Access the Frontend (Whiteboard):**
    Open your web browser and navigate to `http://localhost:5000/`.
    
    To test real-time drawing, open this URL in two different browser tabs or windows. Enter a common room name and unique Peer IDs for each tab, then click "Connect" on both.

### Example API Endpoints (from `app.py`)

These are the API endpoints implemented by the example `app.py` using the `SignalingManager`.

-   **`POST /offer`**: Handles incoming WebRTC SDP offers. Expects `room`, `peer_id`, and `offer` (SDP) in JSON body. Returns an SDP answer.
-   **`POST /candidate`**: Handles incoming ICE candidates. Expects `room`, `peer_id`, and `candidate` (ICE candidate details) in JSON body. Returns `{"status": "ok"}`.
-   **`POST /leave`**: Handles a peer leaving a room. Expects `room` and `peer_id` in JSON body. Returns `{"status": "ok"}`.
-   **`GET /rooms`**: (For debugging/monitoring) Returns a JSON object listing all active rooms and their connected peers.
-   **`GET /`**: Serves the `index.html` frontend application.
-   **`GET /PeerPy_Client/<path:path>`**: Serves other static files (e.g., `PeerPy_Client/myrtclib.js`).

## License

This project is open-sourced under the MIT License. See the [LICENSE](LICENSE) file for details.