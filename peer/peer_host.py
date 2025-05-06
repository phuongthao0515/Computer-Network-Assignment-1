import socket
from threading import Thread, Lock
import json
import queue
import time
from datetime import datetime
from utils.protocol import create_request, parse_request, Command, parse_response, Status, create_response

class PeerHost:
    def __init__(self, channel_name, owner_peer, ip, port, tracker_ip, tracker_port, max_connections=10):
        # Tracker information
        self.tracker_ip = tracker_ip
        self.tracker_port = tracker_port
        
        # Channel information
        self.owner_peer = owner_peer
        self.channel_name = channel_name
        self.ip = ip
        self.port = port
        self.max_connections = max_connections
        
        # Connected peers information
        self.connected_peers = []
        self.peer_lock = Lock()
        
        # Authentication information
        self.authen_peers = {}
        self.authen_peers[self.owner_peer] = {
            "role": "owner",
            "status": "online",
        }
        # self.authen_peers['ben'] = {
        #     "role": "user",
        #     "status": "online",
        # }
        self.authen_peers_lock = Lock()
        
        # Viewers permission
        self.view_permission = True
        
        # Messages information
        self.messages = [
            {"username": "System", "message_content": "Welcome to the channel!", "time": datetime.now().strftime("%H:%M:%S")},
            {"username": "Dien", "message_content": "Hello everyone!", "time": datetime.now().strftime("%H:%M:%S")},
            {"username": "Hieu", "message_content": "Hi Dien!", "time": datetime.now().strftime("%H:%M:%S")}
        ]
        self.messages_lock = Lock()
        self.message_queue = queue.Queue()
        
        # Running manager
        self.socket_server = socket.socket()
        self.socket_server.bind((self.ip, self.port))
        
        # Flag to control threads
        self.running = True

    def listen(self):
        try: 
            status = self.host_submission()
            if status != "OK":
                print("Failed to submit info to tracker.")
                return
                
            self.socket_server.listen(10)
            print(f"Successfully listening on {self.ip}:{self.port}...")
            
            # Start the broadcast thread
            Thread(target=self.broadcast_messages, daemon=True).start()
            
            while self.running:
                conn, addr = self.socket_server.accept()
                with self.peer_lock:
                    if len(self.connected_peers) < self.max_connections:
                        self.connected_peers.append((conn, addr))
                        Thread(target=self.handle_peer_connection, args=(conn, addr), daemon=True).start()
                    else:
                        conn.close()
        except Exception as e:
            print(f"Error: {e}")
            self.running = False
        finally:
            self.socket_server.close()

    # DONE
    def host_submission(self):                
        with socket.socket() as tracker_socket:
            tracker_socket.connect((self.tracker_ip, self.tracker_port))
            
            request = create_request(Command.HOST, {
                "channel_name": self.channel_name,
                "peer_server_ip": self.ip,
                "peer_server_port": self.port
            })
            tracker_socket.send(request)
            response = tracker_socket.recv(1024)
            status, payload = parse_response(response)
            
            if status != Status.OK.value:
                print(f"Failed to submit info to tracker: {payload['status']}")
                return payload['status']
            
            tracker_socket.close()
        
        return status
    
    def handle_peer_connection(self, conn, addr):
        identity = conn.recv(1024)
        command, payload = parse_request(identity)
        if not self.view_permission:
            # Check if the peer is authenticated
            if not self._is_authenticated(payload['username']):
                print(f"Peer {payload['username']} is not authenticated.")
                conn.send(create_response(Status.UNAUTHORIZED, {}))
                print(f"Sending UNAUTHORIZED response to {addr}")
                conn.close()
                return
            
        # Send authentication response
        conn.send(create_response(Status.OK, {
            "status": "success",
            "message": "Authenticated successfully"
        }))
        print(f"Peer {payload['username']} authenticated successfully.")
        # Send initial messages to the new peer
        with self.messages_lock:
            request = create_request(Command.MESSAGE, self.messages)
            conn.send(request)
        
        buffer = ""
        while self.running:
            data = conn.recv(1024)
            buffer += data.decode("utf-8")
            if not data:
                break
            
            while '\\' in buffer:
                # Split the buffer into individual requests
                request, buffer = buffer.split('\\', 1)
                
                if not request:
                    continue
                
                # Parse the request
                try: 
                    command, payload = parse_request(request, isSeparated=True)
                    if command == Command.MESSAGE.value:
                        # Check authentication
                        if not self._is_authenticated(payload[0]['username']):
                            print(f"Peer message {payload[0]['username']} is not authenticated.")
                            conn.send(create_response(Status.UNAUTHORIZED, {}))
                            print(f"Sending UNAUTHORIZED response to {addr}")
                            continue

                        for message in payload:
                            message['time'] = datetime.now().strftime("%H:%M:%S")
                            with self.messages_lock:
                                self.messages.append(message)
                            self.message_queue.put(message)
                        response = create_response(Status.OK, {
                            "status": "success",
                            "message": "Message received"
                        })

                        conn.send(response)
                        
                    elif command == Command.CACHE.value:
                        # Check authentication

                        if not self._is_authenticated(payload[0]['username']):
                            print(f"Peer cache {payload[0]['username']} is not authenticated.")
                            continue

                        for message in payload:
                            message['time'] = datetime.now().strftime("%H:%M:%S")
                            with self.messages_lock:
                                self.messages.append(message)
                            self.message_queue.put(message)
                        # No response needed for cache command
                    elif command == Command.DEBUG.value:
                        with self.messages_lock and self.authen_peers_lock and self.peer_lock:
                            print("DEBUG INFO")
                            print(f"Connected Peers: {[a for _, a in self.connected_peers]}")
                            print(f"Authenticated Peers: {self.authen_peers}")
                            print(f"Messages: {self.messages}")
                            print(f"View Permission: {self.view_permission}")
                            
                    elif command == Command.VIEW.value:
                        if payload['username'] == self.owner_peer:
                            self.view_permission = bool(payload['permission'])
                            response = create_response(Status.OK, {
                                "status": "success",
                                "message": "Permission updated"
                            })
                            conn.send(response)
                        else:
                            response = create_response(Status.UNAUTHORIZED, {
                                "status": "failure",
                                "message": "Permission denied"
                            })
                            conn.send(response)
                        
                except Exception as e:
                    print(f"Error handling peer {addr}: {e}")
                    break
        
        # Remove peer on disconnection
        with self.peer_lock:
            self.connected_peers = [(c, a) for c, a in self.connected_peers if a != addr]
        conn.close()

    # NOT DONE: 
    # Messages should be delivered in list rather than one by one -> Change the protocol, remove BROADCAST command
    # Fetch all messages from the queue and send them to the peers
    # May need thread pooling for sending messages at good performance
    def broadcast_messages(self):
        while self.running:
            try:
                # Get all available messages from the queue (up to a reasonable limit)
                messages_to_send = []
                try:
                    # Get the first message (with timeout)
                    message = self.message_queue.get(timeout=0.1)
                    messages_to_send.append(message)
                    
                    # Try to get more messages without blocking (up to 50)
                    max_batch_size = 50
                    for _ in range(max_batch_size - 1):
                        try:
                            message = self.message_queue.get_nowait()
                            messages_to_send.append(message)
                        except queue.Empty:
                            break
                except queue.Empty:
                    continue  # No messages available, go back to the start of the loop
                
                # Now broadcast all collected messages
                with self.peer_lock:
                    peers = self.connected_peers.copy()
                
                # Process each peer outside the lock to minimize lock holding time
                for conn, addr in peers:
                    try:
                        request = create_request(Command.MESSAGE, messages_to_send)
                        conn.send(request)
                    except (BrokenPipeError, ConnectionResetError):
                        print(f"Peer {addr} disconnected. Removing from list.")
                        with self.peer_lock:
                            self.connected_peers = [(c, a) for c, a in self.connected_peers if a != addr]
                            conn.close()
                    except socket.error as e:
                        print(f"Socket error with {addr}: {e}")
                        with self.peer_lock:
                            self.connected_peers = [(c, a) for c, a in self.connected_peers if a != addr]
                    except Exception as e:
                        print(f"Error broadcasting to {addr}: {e}")
                        with self.peer_lock:
                            self.connected_peers = [(c, a) for c, a in self.connected_peers if a != addr]
                    
            except Exception as e:
                print(f"Error in broadcast thread: {e}")
                time.sleep(1)

    def _is_authenticated(self, username):
        with self.authen_peers_lock:
            return username in self.authen_peers

    def set_view_permission(self, permission):
        self.view_permission = permission

    def stop(self):
        self.running = False
        self.socket_server.close()
        with self.peer_lock:
            for conn, _ in self.connected_peers:
                conn.close()
            self.connected_peers = []