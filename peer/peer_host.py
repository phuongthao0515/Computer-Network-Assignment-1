import socket
from threading import Thread, Lock
from typing import List, Tuple
from utils.message import Message
import json
import queue
import time

class PeerHost:
    def __init__(self, channel_name, ip, port, tracker_ip, tracker_port, max_connections=10):
        self.channel_name = channel_name
        self.ip = ip
        self.port = port
        self.tracker_ip = tracker_ip
        self.tracker_port = tracker_port
        self.max_connections = max_connections
        
        # List of connected peers
        self.connected_peers: List[Tuple] = []
        self.peer_lock = Lock()
        
        # List of messages
        self.messages = [
            Message("System", "Welcome to the channel!"),
            Message("Dien", "Hello everyone!"),
            Message("Hieu", "Hi Dien!"),
        ]
        self.messages_lock = Lock()
        
        # Message queue for broadcasting
        self.message_queue = queue.Queue()
        
        # Create a socket
        self.socket_server = socket.socket()
        self.socket_server.bind((self.ip, self.port))
        
        # Flag to control threads
        self.running = True

    def listen(self):
        try: 
            # Submit info before listening
            status = self.submit_info()
            if status != "OK":
                print("Failed to submit info to tracker.")
                return
                
            self.socket_server.listen(10)
            print(f"Listening on {self.ip}:{self.port}")
            
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

    def submit_info(self):
        data = {
            "command_name": "HOST",
            "channel_name": self.channel_name,
            "peer_server_ip": self.ip,
            "peer_server_port": self.port
        }
        
        with socket.socket() as tracker_socket:
            tracker_socket.connect((self.tracker_ip, self.tracker_port))
            tracker_socket.send(json.dumps(data).encode("utf-8"))
            status = tracker_socket.recv(1024).decode("utf-8")
        
        return status
    
    def handle_peer_connection(self, conn, addr):
        # Send initial messages to the new peer
        with self.messages_lock:
            conn.send(json.dumps([message.to_dict() for message in self.messages]).encode("utf-8"))
        
        while self.running:
            try:
                data = conn.recv(1024).decode("utf-8")
                if not data:
                    break
                data = json.loads(data)
                
                if data['command_name'] == "MESSAGE":
                    message = Message(data['username'], data['message_content'])
                    with self.messages_lock:
                        self.messages.append(message)
                    self.message_queue.put((message, addr))
            except Exception as e:
                print(f"Error handling peer {addr}: {e}")
                break
        
        # Remove peer on disconnection
        with self.peer_lock:
            self.connected_peers = [(c, a) for c, a in self.connected_peers if a != addr]
        conn.close()

    def broadcast_messages(self):
        while self.running:
            try:
                message, sender_addr = self.message_queue.get(timeout=1.0)
                message_dict = message.to_dict()
                message_data = json.dumps(message_dict).encode("utf-8")
                
                with self.peer_lock:
                    for conn, addr in self.connected_peers:
                        if addr != sender_addr:  # Prevent sending back to the sender
                            try:
                                conn.send(message_data)
                            except Exception as e:
                                print(f"Error broadcasting to {addr}: {e}")
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Error in broadcast thread: {e}")
                time.sleep(1)

    def stop(self):
        self.running = False
        self.socket_server.close()
        with self.peer_lock:
            for conn, _ in self.connected_peers:
                conn.close()
            self.connected_peers = []