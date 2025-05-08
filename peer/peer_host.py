import socket
from threading import Thread, Lock
import queue
import time
from uuid import uuid4
from datetime import datetime
from utils.protocol import create_request, parse, Command, Status, create_response
from utils.utils import UserType

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
            "status": "offline",
        }
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
        
        # Request tracking mechanism
        self.pending_responses = {}
        self.response_queues_lock = Lock()
        
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
                Thread(target=self.handle_peer_connection, args=(conn, addr), daemon=True).start()
                # with self.peer_lock:
                #     if len(self.connected_peers) < self.max_connections:
                #         self.connected_peers.append((conn, addr))
                #         Thread(target=self.handle_peer_connection, args=(conn, addr), daemon=True).start()
                #     else:
                #         conn.close()
        except Exception as e:
            print(f"Error: {e}")
            self.running = False
        finally:
            self.socket_server.close()

    # OK
    def host_submission(self):
        try:             
            with socket.socket() as tracker_socket:
                tracker_socket.connect((self.tracker_ip, self.tracker_port))
                
                # One time socket connection so no need to keep it open
                request = create_request(Command.HOST, {
                    "channel_name": self.channel_name,
                    "peer_server_ip": self.ip,
                    "peer_server_port": self.port,
                    "view_permission": self.view_permission
                })
                tracker_socket.send(request)
                
                response = tracker_socket.recv(1024)
                status, _, _ = parse(response)
                
                if status == Status.OK.value:
                    print(f"Successfully submitted info to tracker")
                else:
                    print(f"Unexpected response from tracker: {status}")
                           
            return status
        except Exception as e:
            print(f"Error connecting to tracker: {e}")
            return "ERROR"
        finally:
            tracker_socket.close()
    
    # 
    def handle_peer_connection(self, conn, addr):
        # Handling limit of connections
        with self.peer_lock:
            if len(self.connected_peers) >= self.max_connections:
                print(f"Max connections reached. Closing connection from {addr}.")
                conn.close()
                return
        try:   
            # Handling CONNECT command
            connect_request = conn.recv(1024)
            command, payload, request_id = parse(connect_request)
            
            # Store username for later cleanup
            username = payload.get('username')
            
            if command != Command.CONNECT.value:
                print(f"Invalid command from {addr}: {command}")
                conn.send(create_response(request_id, Status.REQUEST_ERROR, {}))
                conn.close()
                return
            
            if not self.view_permission:
                if not self._is_authenticated(payload['username']):
                    print(f"Peer {payload['username']} is not authenticated.")
                    conn.send(create_response(request_id, Status.UNAUTHORIZED, {}))
                    conn.close()
                    return
                
            with self.messages_lock:
                conn.send(create_response(request_id, Status.OK, self.messages))
            print(f"Peer {payload['username']} authenticated successfully.")
            
            with self.peer_lock:
                self.connected_peers.append((conn, addr, payload))
                print(f"Connected peers: {[(a, u) for _, a, u in self.connected_peers]}")
            
            with self.authen_peers_lock:
                if payload['username'] in self.authen_peers:
                    if payload['invisible'] is True:
                        self.authen_peers[payload['username']]['status'] = 'offline'
                    else:
                        self.authen_peers[payload['username']]['status'] = 'online'
                    
            # Listening loop
            buffer = ""
            while self.running:
                data = conn.recv(1024)
                buffer += data.decode("utf-8")
                if not data:
                    break
                
                while '\n' in buffer:
                    request, buffer = buffer.split('\n', 1)
                    if not request:
                        continue
                    
                    try: 
                        command, payload, request_id = parse(request, isSeparated=True)
                        if command == Command.MESSAGE.value:
                            # Check authentication
                            if not self._is_authenticated(payload[0]['username']):
                                print(f"Peer message {payload[0]['username']} is not authenticated.")
                                conn.send(create_response(request_id, Status.UNAUTHORIZED, {}))
                                print(f"Sending UNAUTHORIZED response to {addr}")
                                continue

                            for message in payload:
                                message['time'] = datetime.now().strftime("%H:%M:%S")
                                with self.messages_lock:
                                    self.messages.append(message)
                                self.message_queue.put(message)
                            response = create_response(request_id, Status.OK, {})

                            conn.send(response)
                            
                            # No response needed for cache command
                        elif command == Command.DEBUG.value:
                            with self.messages_lock and self.authen_peers_lock and self.peer_lock:
                                print("DEBUG INFO")
                                print(f"Connected Peers: {[(a, u) for _, a, u in self.connected_peers]}")
                                print(f"Authenticated Peers: {self.authen_peers}")
                                print(f"Messages: {self.messages}")
                                print(f"View Permission: {self.view_permission}")
                                
                        elif command == Command.VIEW.value:                                
                            # Set view
                            if payload['username'] == self.owner_peer:
                                self.view_permission = bool(payload['permission'])
                                
                                with socket.socket() as tracker_socket:
                                    tracker_socket.connect((self.tracker_ip, self.tracker_port))
                                    
                                    request = create_request(Command.VIEW, {
                                        "channel_name": self.channel_name,
                                        "view_permission": self.view_permission
                                    })
                                    tracker_socket.send(request)
                                    
                                    response = tracker_socket.recv(1024)
                                    status, _, _ = parse(response)
                                    
                                    if status == Status.OK.value:
                                        print(f"Successfully updated view permission to {self.view_permission} on tracker")
                                    else:
                                        print(f"Unexpected response from tracker: {status}")
                                
                                response = create_response(request_id, Status.OK, {})
                                conn.send(response)
                            else:
                                response = create_response(request_id, Status.UNAUTHORIZED, {})
                                conn.send(response)
                                
                        elif command == Command.RET_INFO.value:
                            with self.authen_peers_lock:
                                if payload['username'] not in self.authen_peers:
                                    response = create_response(request_id, Status.UNAUTHORIZED, {
                                        "message": "You are not authorized to view this information."
                                    })
                                    conn.send(response)
                                    continue
                            
                            with self.authen_peers_lock and self.messages_lock:
                                response = create_response(request_id, Status.OK, {
                                    "messages": self.messages,
                                    "authen_peers": self.authen_peers,
                                    "view_permission": self.view_permission,
                                })
                                conn.send(response)
                                
                        elif command == Command.INVISIBLE.value:
                            print(0)
                            with self.authen_peers_lock:
                                if payload['username'] not in self.authen_peers:
                                    response = create_response(request_id, Status.UNAUTHORIZED, {
                                        "message": f"You are not authenticated user of channel {self.channel_name}. So your status is not stored."
                                    })
                                    conn.send(response)
                                    continue

                            if payload['invisible'] is True:
                                with self.authen_peers_lock:
                                    self.authen_peers[payload['username']]['status'] = 'offline'
                                with self.peer_lock:
                                    for _, _, user in self.connected_peers:
                                        if user['username'] == payload['username']:
                                            user['invisible'] = True
                                            break
                            else:
                                with self.authen_peers_lock:
                                    self.authen_peers[payload['username']]['status'] = 'online'
                                with self.peer_lock:
                                    for _, _, user in self.connected_peers:
                                        if user['username'] == payload['username']:
                                            user['invisible'] = False
                                            break
                                    
                            response = create_response(request_id, Status.OK, {
                                "message": f"Your status has been updated to {'offline' if payload['invisible'] else 'online'}."
                            })
                            conn.send(response)
                                
                        elif command == Command.AUTHORIZE.value:
                            author_type = payload['author_type']
                            actor = payload['actor']
                            if actor != self.owner_peer:
                                response = create_response(request_id, Status.UNAUTHORIZED, {
                                    "message": "Only the owner can authorize users."
                                })
                                conn.send(response)
                                continue
                            
                            target = payload['target']
                            target_type = None
                            with self.peer_lock:
                                for _, _, user in self.connected_peers:
                                    if user['username'] == target:
                                        target_type = user['user_type']
                                        status = "online" if user['invisible'] is False else "offline"
                                        break

                            if target_type is None:
                                response = create_response(request_id, Status.REQUEST_ERROR, {
                                    "message": f"User {target} is not connected."
                                })
                                conn.send(response)
                                continue
                                    
                            if target_type == UserType.GUEST.value:
                                response = create_response(request_id, Status.REQUEST_ERROR, {
                                    "message": "Cannot authorize a guest."
                                })
                                conn.send(response)
                                continue
                            
                            if author_type == 0:
                                with self.authen_peers_lock:
                                    if target in self.authen_peers:
                                        del self.authen_peers[target]
                                        response = create_response(request_id, Status.OK, {
                                            "message": f"User {target} has been deauthorized."
                                        })
                                        conn.send(response)
                                    else:
                                        response = create_response(request_id, Status.REQUEST_ERROR, {
                                            "message": f"User {target} is not authorized."
                                        })
                                        conn.send(response)
                                continue
                            
                            elif author_type == 1:                                    
                                with self.authen_peers_lock:
                                    if target not in self.authen_peers:
                                        self.authen_peers[target] = {
                                            "role": "user",
                                            "status": status,
                                        }
                                        response = create_response(request_id, Status.OK, {
                                            "message": f"User {target} has been authorized."
                                        })
                                        conn.send(response)
                                    else:
                                        response = create_response(request_id, Status.REQUEST_ERROR, {
                                            "message": f"User {target} is already authorized."
                                        })
                                        conn.send(response)
                                continue
                                
                            else:
                                response = create_response(request_id, Status.REQUEST_ERROR, {
                                    "message": "Invalid author type."
                                })
                                conn.send(response)
                        
                        else:
                            print(f"Unknown command from {addr}: {command}")                         
                            
                    except Exception as e:
                        print(f"Error handling peer {addr}: {e}")
                        break
        except Exception as e:
            print(f"Error in connection handler: {e}")
        finally:
            # Remove peer on disconnection
            with self.peer_lock:
                self.connected_peers = [(c, a, u) for c, a, u in self.connected_peers if a != addr]
            
            with self.authen_peers_lock:
                if username and username in self.authen_peers:
                    self.authen_peers[username]['status'] = 'offline'       
            conn.close()
            print("Finish clean up")

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
                for conn, addr, user in peers:
                    try:
                        request = create_request(Command.MESSAGE, messages_to_send)
                        conn.send(request)
                    except (BrokenPipeError, ConnectionResetError):
                        print(f"Peer {addr} disconnected. Removing from list.")
                        with self.peer_lock:
                            self.connected_peers = [(c, a, u) for c, a, u in self.connected_peers if a != addr]
                        with self.authen_peers_lock:
                            if user['username'] in self.authen_peers:
                                self.authen_peers[user['username']]['status'] = 'offline'
                        conn.close()
                    except socket.error as e:
                        print(f"Socket error with {addr}: {e}")
                        with self.peer_lock:
                            self.connected_peers = [(c, a, u) for c, a, u in self.connected_peers if a != addr]
                        with self.authen_peers_lock:
                            if user['username'] in self.authen_peers:
                                self.authen_peers[user['username']]['status'] = 'offline'
                    except Exception as e:
                        print(f"Error broadcasting to {addr}: {e}")
                        with self.peer_lock:
                            self.connected_peers = [(c, a, u) for c, a, u in self.connected_peers if a != addr]
                        with self.authen_peers_lock:
                            if user['username'] in self.authen_peers:
                                self.authen_peers[user['username']]['status'] = 'offline'
                        
                    
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
            for conn, _, _ in self.connected_peers:
                conn.close()
            self.connected_peers = []
            
    def send_request_and_wait_response(self, conn, command, payload, timeout=5.0):
        request_id = str(uuid4())
        request = create_request(command, payload, request_id)
        
        # Response queue
        response_queue = queue.Queue()
        
        # Register the request
        with self.response_queues_lock:
            self.pending_responses[request_id] = response_queue
            
        try: 
            conn.send(request)
            
            try: 
                # Wait for response
                response = response_queue.get(timeout=timeout)
                status, payload, _ = parse(response)
                return status, payload
            except queue.Empty:
                print(f"Request timed out after {timeout} seconds")
                return None, None
        
        except Exception as e:
            print(f"Error sending request: {e}")
            return None, None
        
        finally:
            # Unregister the request
            with self.response_queues_lock:
                if request_id in self.pending_responses:
                    del self.pending_responses[request_id]