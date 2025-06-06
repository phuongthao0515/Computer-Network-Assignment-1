# Hybrid implementation for chat application (Discord-like)

## 📚 Table of Contents

- [Overview](#overview)
- [How to Run](#how-to-run)
  - [Prerequisites](#prerequisites)
  - [Start the Tracker (Central Server)](#1-start-the-tracker-central-server)
  - [Start the Peer (Clients/Host)](#2-start-the-peer-clientshost)
- [Features](#features)
  - [Core Functionality](#core-functionality)
  - [User Management](#user-management)
  - [Channel Management](#channel-management)
  - [Advanced Peer Features](#advanced-peer-features)
- [System Design](#system-design)
  - [1. Communication Protocol](#1communication-protocol)
  - [2. Tracker Design](#2-tracker-design)
  - [3. Peer Design](#3-peer-design)
- [Possible Errors](#possible-errors)
- [Note](#note)

## Overview
This project implements a hybrid chat system combining the client-server and peer-to-peer (P2P) paradigms to efficiently broadcast data across a network of peers. It utilizes a central Tracker server for peer discovery and channel listing. Peers can act as Hosts by creating and managing chat channels, or as Clients by joining existing channels to send and receive messages.

The application supports:
- Guest access or sign in/sign up for an account
- Realtime messaging within channels
- Hosting new channel
- Client-side message caching for offline messages
- Channel view switch (public/private) and user authorization within channels
- An interactive command-line interface (CLI) for advanced operations and debug.
- A graphical user interface (GUI) built with Tkinter for a user-friendly experience (though the main execution in peer.py currently defaults to the CLI). 

## How to Run:
You can run the tracker on one machine or in Virtual Machine (VM), and then run multiple peers on the same or different machines/VMs.
### Prerequisites:
- Python 3.x (standard libraries like `socket`, `json`, `threading`, `datetime`, `tkinter`,... are used).

### 1. Start the Tracker (Central Server)
Run the tracker script:  
```bash
# In Windows:
python tracker.py

# In Linux:
python3 tracker.py
```
By default, the tracker will listen on '192.168.56.101:22236'. This is hardcoded in tracker.py. You can change it.

### 2. Start the peer (clients/host):
Peers connect to the tracker to get a list of channels and can either join existing channels or host new ones.
- To run a peer that only acts as a client (does not host a channel):
```
python peer.py --tracker-ip <TRACKER_IP> --tracker-port <TRACKER_PORT> --username <YOUR_USERNAME>
```
Example:
```bash
python peer.py --tracker-ip 192.168.56.101 --tracker-port 22236 --username Alice
```
- To run a peer that also hosts a channel: Provide `--peer-host-ip`, `--peer-host-port` (or let it be random if 0), and `--channel-name`.
```bash
python peer.py --tracker-ip <TRACKER_IP> --tracker-port <TRACKER_PORT> --peer-host-ip <PEER_HOST_IP> --peer-host-port <PEER_HOST_PORT> --channel-name <CHANNEL_NAME> --username <YOUR_USERNAME>
```
**Sample commands (from `peer.py`):**
* Peer 1 (Ken) hosts "first" channel on port 20000:
```bash
python peer.py --tracker-ip 192.168.56.102 --tracker-port 22236 --peer-host-ip 192.168.56.102 --peer-host-port 20000 --channel-name first --username ken
```
* Peer 2 (Ben) hosts "second" channel on port 20001:
```bash
python peer.py --tracker-ip 192.168.56.103 --tracker-port 22236 --peer-host-ip 192.168.56.103 --peer-host-port 20001 --channel-name second --username ben
```
* Peer 3 (Charlie) joins as a client:
```bash
 python peer.py --tracker-ip 192.168.56.104 --tracker-port 22236 --username charlie
 ```

**Key `peer.py` arguments:**
*   `--tracker-ip`: IP address of the tracker (default: `localhost`).
*   `--tracker-port`: Port of the tracker (default: `5000`, **but the tracker runs on `22236`, so ensure you use `--tracker-port 22236`**).
*   `--peer-host-ip`: IP address for this peer to host its channel on (default: `localhost`).
*   `--peer-host-port`: Port for this peer to host its channel on (default: `0` for a random port).
*   `--channel-name`: Name of the channel to host. If empty, the peer runs in client-only mode.
*   `--username`: Username for the client (default: `User`).

    Once a peer is running, it will launch a command-line interface (CLI) by default. The GUI can be enabled by modifying the `if __name__ == "__main__":` block in `peer.py`. 


## Features

### Core Functionality
- **P2P Chat:** Enables direct communication between peers after initial connection via a host.
- **Multi-channel Support:** Users can join and participate in multiple chat channels.
- **Graphical User Interface (GUI):** A Tkinter-based GUI provides pages for:
    - Login/Signup/Guest Access
    - Channel Listing & Joining
    - Real-time Messaging within selected channels
- **Command-Line Interface (CLI):** An interactive CLI for users who prefer text-based interaction, offering a comprehensive set of commands.

### User Management
- **User Signup/Signin:** Registered users can sign up and sign in via the tracker. Authenticated users have distinct capabilities. 
- **Guest Access:** Users can join as guests with a temporary username.
- **Username Association:** Messages are tagged with the sender's username.
- **Invisible Mode:** Registered users can choose to be "invisible," which affects their online status display on channels they are part of, without preventing them from receiving messages.

### Channel Management
- **Channel Hosting:** Peers can create and host new chat channels. The channel owner has special privileges.
- **Dynamic Channel Discovery:** Clients fetch a list of available channels from the tracker.
- **Joining/Disconnecting Channels:** Clients can join and leave channels dynamically.
- **View Permissions:** Channel owners can set their channel's view permission (publicly viewable or restricted). This is registered with the tracker and enforced by the host.
- **User Authorization:** Channel owners can authorize specific registered users to participate or have special roles within their channel (e.g., allowing message sending if the channel is otherwise restricted).

### Advanced Peer Features
- **Client-Side Message Caching:** If a client attempts to send a message to a channel it's not currently connected to, or if the connection drops, the message is cached locally. Cached messages are automatically sent when the client successfully (re)connects to the channel.
- **Message Broadcasting:** Peer hosts efficiently broadcast new messages to all connected clients in their channel.
- **Debug Information:** CLI commands allow for retrieving debug information from clients and hosts.

## System Design:
### 1.Communication Protocol
- **JSON-based Protocol:** A custom protocol using JSON for message bodies ensures structured communication between peers and the tracker.
- **Command-Based Interaction:** Defined commands (`LIST`, `HOST`, `MESSAGE`, `SIGNIN`, `SIGNUP`, `GUEST`, `CONNECT`, `VIEW`, `AUTHORIZE`, `RET_INFO`, `INVISIBLE`, etc.) manage actions and data exchange.
- **Request/Response IDs:** Each request has a unique ID, which is included in the response, allowing for reliable matching. 
- **Status Codes:** Responses include status codes (`OK`, `REQUEST_ERROR`, `SERVER_ERROR`, `UNAUTHORIZED`) to indicate the outcome of operations.
- Each message ends with a special separator (`\n`) to differentiate requests in the stream-based socket communication.
  
### 2. Tracker Design:
 The tracker is essential for peers to discover each other and list available channels. Its main responsibilities include:

- Listening for client connections: there is a thread for continuously listening on a specific IP and port. When accepting new socket connections a new thread is spawned (handle_user_submission) to handle each client.

- Handle requests: Each request from the client is parsed and handled based on its command type (as in protocol). For each request, a new thread is created.

- Data Synchronization and Concurrency: Uses Lock objects to synchronize access to shared resources: `account_list`, `channel_list`, and `visitor_list`. 

### 3. Peer Design:
Peers can act as either hosts or clients. A key design challenge is matching asynchronous responses to their originating requests. This project implements a robust mechanism for this, primarily within the PeerClient and PeerHost when they interact with other services (like the tracker or another peer):

Here's how it works:

1.  **Unique Request ID Generation:**
    - When a client (e.g., `PeerClient`) needs to send a request (e.g., to a `PeerHost` or the `Tracker`), it generates a unique `request_id` (a UUID) using the `create_request` function in `utils/protocol.py`.
    - This `request_id` is embedded within the JSON payload of the request.

2.  **Tracking Pending Responses:**
    - The `PeerClient` (and `PeerHost` for its own outgoing requests) maintains a dictionary called `pending_responses`.
    - Before sending a request, it creates a `queue.Queue` object and stores it in `pending_responses` with the `request_id` as the key: `self.pending_responses[request_id] = response_queue`.

3.  **Sending the Request and Waiting:**
    - The request (containing the `request_id`) is sent to the server (PeerHost or Tracker).
    - The sending code then blocks, waiting to get an item from the `response_queue` associated with that `request_id` (e.g., `response_queue.get(timeout=...)`).

4.  **Server Processing and Response:**
    - The server (PeerHost or Tracker) receives the request, parses it, and extracts the `request_id`.
    - After processing, the server constructs a response using `create_response`. Crucially, it includes the *original* `request_id` in this response.

5.  **Client-Side Response Handling:**
    - The `PeerClient`'s dedicated message-listening thread (`listen_for_messages`) continuously receives data from connected sockets.
    - When a complete message (which could be a response from a server) is received, it's parsed.
    - If the parsed message is identified as a response (based on its header, e.g., "OK", "ERROR"), the `request_id` is extracted from its body.
    - The listening thread then looks up this `request_id` in its `pending_responses` dictionary and puts the entire raw response message into the corresponding `queue.Queue`.

6.  **Unblocking and Processing the Response:**
    - The `response_queue.get()` call in the original sending code (from step 3) unblocks because an item (the response) has been added to its queue.

7.  **Cleanup:**
    - After the response is received or a timeout occurs, the `request_id` and its queue are removed from `pending_responses` to prevent memory leaks.

This mechanism ensures that even with multiple concurrent requests and asynchronous replies, each part of the client code receives the correct response for the request it initiated.


## Possible errors:
- Authentication-relate errors: wrong username or password, user 
- Connection Failed
- Data Loss: due to network instability 
- Port Binding:	assign host at the same port (do mình đang sài local host?)

## Note:
