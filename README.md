# PeerPyRTC

**A simple, modern Python and JavaScript library for building real-time WebRTC DataChannel applications.**

PeerPyRTC provides a high-level API to abstract away the complexities of WebRTC, allowing you to build peer-to-peer data communication into your web applications with ease. It's designed to be modular, flexible, and easy to integrate with any Python backend framework.

## Features

-   **High-Level Abstraction**: Simple, intuitive APIs for both backend (Python) and frontend (JavaScript).
-   **Framework-Agnostic Backend**: Easily integrates with Flask, FastAPI, Django, or any other Python web framework.
-   **Automatic Message Relay**: Messages sent by one peer are automatically and efficiently broadcast to all other peers in the same room.
-   **Backend Message Handling**: An elegant decorator-based system (`@SignalingManager.message_handler`) allows your backend to process, persist, or moderate messages.
-   **Server-Sent Broadcasts**: Includes a `Broadcaster` utility for the backend to send messages to all clients in a room.
-   **Zero-Config TURN Servers**: Comes with default TURN servers pre-configured to help traverse restrictive firewalls.

## Installation

### Backend (Python)
```bash
pip install peerpyrtc
```

### Frontend (JavaScript)
```bash
npm install peerpyrtc-client
```

## Quick Start

This example demonstrates how to set up a minimal signaling server with Flask.

### Backend (`app.py`)

```python
from flask import Flask, request, jsonify
from peerpyrtc import SignalingManager

app = Flask(__name__)
signaling_manager = SignalingManager()

@app.route("/offer", methods=["POST"])
def offer():
    return jsonify(signaling_manager.offer(**request.json))

@app.route("/candidate", methods=["POST"])
def candidate():
    signaling_manager.candidate(**request.json)
    return jsonify({"status": "ok"})

@app.route("/leave", methods=["POST"])
def leave():
    signaling_manager.leave(**request.json)
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
```

### Frontend (`main.js`)

```javascript
import { WebRTCConnection } from 'peerpyrtc-client';

const rtc = new WebRTCConnection("my-room-name");

rtc.onMessage = (senderId, message) => {
  console.log(`Received message from ${senderId}:`, message);
};

rtc.onOpen = () => {
  console.log("Connection open! Ready to send messages.");
  rtc.sendMessage("Hello from the new peer!");
};

// Use an async function to connect
async function main() {
  await rtc.connect();
}

main();
```
*Note: The frontend code assumes you are using a bundler like Webpack, Rollup, or Vite to handle the `npm` package import.*

## Backend API Reference (`peerpyrtc`)

### `SignalingManager`

The main class for managing rooms and signaling on the backend.

`__init__(self, debug=False)`
:   Initializes the signaling manager. Set `debug=True` to enable detailed logging.

`offer(self, room: str, peer_id: str, offer: dict) -> dict`
:   Processes a WebRTC offer from a client. Creates a room if it doesn't exist and returns an SDP answer.

`candidate(self, room: str, peer_id: str, candidate: dict)`
:   Processes an ICE candidate from a client.

`leave(self, room: str, peer_id: str)`
:   Handles a peer leaving a room and performs cleanup.

#### Backend Message Handling with `@message_handler`

While peers communicate directly, you often need the backend to be aware of messages for persistence (database), moderation, or analytics. The `@message_handler` decorator provides a "tap" into the message stream.

The decorated `async` function receives a copy of every message sent between peers, allowing you to process it on the backend without interrupting the real-time P2P flow.

**Example: Saving Messages to a Database**
```python
import asyncio
from peerpyrtc import SignalingManager

# In a real app, this would be your actual database client
class MockDatabase:
    async def save_message(self, room, user, text):
        print(f"Saving to DB: Room({room}) | {user}: {text}")
        await asyncio.sleep(0.1) # Simulate async DB write

db = MockDatabase()
signaling_manager = SignalingManager()

@signaling_manager.message_handler
async def save_all_messages(room_name: str, sender_id: str, message: str):
    """
    This function is called for every message sent in any room.
    """
    await db.save_message(room_name, sender_id, message)

```

### `Broadcaster`

A helper class to broadcast messages from the backend to all clients in a room.

`__init__(self, signaling_manager: SignalingManager)`
:   Initializes the broadcaster.

`broadcast(self, room_name: str, message: str)`
:   Sends a message to all peers in the specified room.

## Frontend API Reference (`peerpyrtc_client`)

### `WebRTCConnection`

The main class for managing the WebRTC connection on the frontend.

`constructor(roomName: string, options: object = {})`
:   Creates a new connection instance.
    -   `roomName`: The name of the room to join.
    -   `options.peerId`: (Optional) A unique ID for this peer. If not provided, a random one is generated.
    -   `options.debug`: (Optional) Set to `true` to enable detailed console logging.

`async connect()`
:   Initiates the connection to the signaling server and establishes the peer-to-peer connection.

`sendMessage(message: string)`
:   Sends a message to all other peers in the room.

`closeConnection()`
:   Closes the connection and notifies the server.

`isConnected() -> boolean`
:   Returns `true` if the data channel is open and ready to send messages.

#### Callbacks

You can assign your own functions to these properties to handle events.

`onMessage = (senderId: string, message: string) => {}`
:   Called when a message is received from another peer. `senderId` is the ID of the peer who sent the message.

`onOpen = () => {}`
:   Called when the data channel is successfully opened and ready for communication.

`onClose = () => {}`
:   Called when the connection is closed.

`onError = (error: Error) => {}`
:   Called when a connection error occurs.

## Examples

The repository includes several examples in the `/examples` directory:

-   **Chat**: A full-featured, multi-room chat application.
-   **Terminal Chat**: A unique example where the Python backend can act as a participant in the chat.
-   **Whiteboard**: A real-time collaborative whiteboard.
-   **Echo**: A simple echo client for testing connectivity.

To run an example, navigate to its directory and run `python app.py`, then open your browser to `http://localhost:5000`.