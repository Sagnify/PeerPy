# peerpyrtc-client

**A simple, modern JavaScript client for building real-time WebRTC DataChannel applications with a PeerPyRTC backend.**

This package provides a high-level JavaScript client that handles all the complexities of WebRTC, allowing you to easily connect to a `peerpyrtc` backend and establish peer-to-peer data connections.

This package contains the **frontend client**. It requires a backend running the `peerpyrtc` Python library.

## Features

-   **High-Level Abstraction**: A simple, event-driven API that abstracts away `RTCPeerConnection` and `RTCDataChannel` boilerplate.
-   **Automatic Connection Handling**: Manages the entire signaling lifecycle (offer, answer, ICE candidates) with the backend.
-   **Event-Driven**: Use callbacks like `onMessage`, `onOpen`, and `onClose` to react to connection events.
-   **Zero-Config TURN Servers**: Comes with default TURN servers pre-configured to help traverse restrictive firewalls.
-   **Lightweight and Modern**: A modern ES module with no external dependencies.

## Installation

```bash
npm install peerpyrtc-client
```

## Quick Start

This example demonstrates how to connect to a `peerpyrtc` backend and start sending messages.

```javascript
import { WebRTCConnection } from 'peerpyrtc-client';

// Create a connection for a specific room.
// A random peer ID will be generated automatically.
const rtc = new WebRTCConnection("my-cool-room");

// Fired when a message is received from another peer.
rtc.onMessage = (senderId, message) => {
  console.log(`Received message from ${senderId}:`, message);
};

// Fired when the data channel is open and ready.
rtc.onOpen = () => {
  console.log("Connection is open! Ready to send messages.");
  rtc.sendMessage("Hello everyone, I'm a new peer!");
};

// Fired if the connection closes or fails.
rtc.onClose = () => {
  console.log("Connection has been closed.");
};

// Connect to the backend and establish the P2P connection.
async function main() {
  try {
    await rtc.connect();
  } catch (error) {
    console.error("Failed to connect:", error);
  }
}

main();
```
*Note: This code assumes you are using a bundler like Webpack, Rollup, or Vite to handle the `npm` package import and that a compatible `peerpyrtc` backend is running and accessible.*

## Frontend API Reference

### `WebRTCConnection`

The main class for managing the WebRTC connection on the frontend.

`constructor(roomName: string, options: object = {})`
:   Creates a new connection instance.
    -   `roomName`: The name of the room to join.
    -   `options.peerId`: (Optional) A unique ID for this peer. If not provided, a random one is generated.
    -   `options.debug`: (Optional) Set to `true` to enable detailed console logging.

`async connect()`
:   Initiates the connection to the signaling server and establishes the peer-to-peer connection. This is the main method to start the WebRTC session.

`sendMessage(message: string)`
:   Sends a message to all other peers in the room over the data channel.

`closeConnection()`
:   Gracefully closes the WebRTC connection and notifies the signaling server.

`isConnected() -> boolean`
:   Returns `true` if the data channel is open and ready to send messages, `false` otherwise.

#### Callbacks

You can assign your own functions to these properties to handle events from the `WebRTCConnection` instance.

`onMessage = (senderId: string, message: string) => {}`
:   Called when a message is received from another peer.
    -   `senderId`: The unique ID of the peer who sent the message.
    -   `message`: The content of the message.

`onOpen = () => {}`
:   Called when the data channel is successfully opened and ready for communication. This is the ideal place to enable UI elements for sending messages.

`onClose = () => {}`
:   Called when the connection is closed, either intentionally or due to a network issue.

`onError = (error: Error) => {}`
:   Called when a connection error occurs.

## Full Examples

The official GitHub repository for `peerpyrtc` contains several full-stack examples that demonstrate how to use this client library with the Python backend. These examples are the best place to see the library in action.
