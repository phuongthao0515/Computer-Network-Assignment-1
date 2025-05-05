import socket
from threading import Thread, Lock
import json
import queue
import time
from datetime import datetime
from utils.protocol import create_request, parse_request, Command, parse_response, Status

class PeerHost:
    def __init__(self, channel_name, ip, port, tracker_ip, tracker_port, max_connections=10):
        # Tracker information
        self.tracker_ip = tracker_ip
        self.tracker_port = tracker_port
        
        # Channel information
        self.channel_name = channel_name
        self.ip = ip
        self.port = port
        self.max_connections = max_connections
        
        # Connected peers information
        self.connected_peers = []
        self.peer_lock = Lock()
        
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

    def host_submission(self):
        data = create_request(Command.HOST, {
            "channel_name": self.channel_name,
            "peer_server_ip": self.ip,
            "peer_server_port": self.port
        })
                
        with socket.socket() as tracker_socket:
            tracker_socket.connect((self.tracker_ip, self.tracker_port))
            tracker_socket.send(data)
            data = tracker_socket.recv(1024)
            status, payload = parse_response(data)
            if status != Status.OK.value:
                print(f"Failed to submit info to tracker: {payload['status']}")
                return payload['status']
            tracker_socket.close()
        
        return status
    
    def handle_peer_connection(self, conn, addr):
        # Send initial messages to the new peer
        with self.messages_lock:
            request = create_request(Command.MESSAGE, self.messages)
            conn.send(request)
        
        while self.running:
            try:
                data = conn.recv(1024)
                if not data:
                    break
                command, payload = parse_request(data)
                
                if command == Command.MESSAGE.value:
                    message = {
                        "username": payload['username'],
                        "message_content": payload['message_content'],
                        "time": datetime.now().strftime("%H:%M:%S")
                    }
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

    # NOT DONE: 
    # Messages should be delivered in list rather than one by one -> Change the protocol, remove BROADCAST command
    # Fetch all messages from the queue and send them to the peers
    # May need thread pooling for sending messages at good performance
    def broadcast_messages(self):
        while self.running:
            try:
                message, sender_addr = self.message_queue.get(timeout=0.1)
                message_data = create_request(Command.MESSAGE, message)
                
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

    # def stop(self):
    #     self.running = False
    #     self.socket_server.close()
    #     with self.peer_lock:
    #         for conn, _ in self.connected_peers:
    #             conn.close()
    #         self.connected_peers = []