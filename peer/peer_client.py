import socket
import json
from threading import Thread, Lock
from typing import List
from utils.message import Message
import time

class PeerClient:
    def __init__(self, username: str, tracker_ip: str, tracker_port: int):
        self.username = username
        self.tracker_ip = tracker_ip
        self.tracker_port = tracker_port
        self.current_host = None
        self.current_socket = None
        self.messages: List[Message] = []
        self.messages_lock = Lock()
        self.running = False
        self.cached_messages: List[str] = []
        self.cached_messages_file = f"{username}_cached_messages.json"
        self._load_cached_messages()

    def get_peer_hosts(self) -> List[dict]:
        """
        Send a request to the tracker to get the list of available peer hosts.
        Returns a list of dictionaries containing host information.
        """
        data = {
            "command_name": "LIST"
        }
        try:
            with socket.socket() as tracker_socket:
                tracker_socket.connect((self.tracker_ip, self.tracker_port))
                tracker_socket.send(json.dumps(data).encode("utf-8"))
                response = tracker_socket.recv(4096).decode("utf-8")
                hosts = json.loads(response)
                return hosts
        except Exception as e:
            print(f"Error getting peer hosts from tracker: {e}")
            return []

    def connect_to_host(self, host_ip: str, host_port: int) -> bool:
        """
        Connect to a specific peer host to fetch and send messages.
        Returns True if connection is successful, False otherwise.
        """
        try:
            if self.current_socket:
                self.current_socket.close()
            
            self.current_socket = socket.socket()
            self.current_socket.connect((host_ip, host_port))
            self.current_host = (host_ip, host_port)
            self.running = True
            
            # Receive initial messages
            data = self.current_socket.recv(4096).decode("utf-8")
            initial_messages = json.loads(data)
            with self.messages_lock:
                self.messages = []
                for msg in initial_messages:
                    if isinstance(msg, dict) and 'username' in msg and 'message_content' in msg:
                        self.messages.append(Message.from_dict(msg))
                    else:
                        print(f"Warning: Invalid message format received: {msg}")
            
            # Start a thread to listen for new messages
            Thread(target=self.listen_for_messages, daemon=True).start()
            print(f"Connected to host {host_ip}:{host_port}")
            
            # Send any cached messages
            self._send_cached_messages()
            return True
        except Exception as e:
            print(f"Error connecting to host {host_ip}:{host_port}: {e}")
            self.current_host = None
            self.current_socket = None
            return False

    def listen_for_messages(self):
        """Listen for incoming messages from the current host."""
        # Set a timeout to allow checking the running flag periodically
        if self.current_socket:
            self.current_socket.settimeout(1.0)
        while self.running and self.current_socket:
            try:
                data = self.current_socket.recv(1024).decode("utf-8")
                if not data:
                    break
                message_data = json.loads(data)
                message = Message.from_dict(message_data)
                with self.messages_lock:
                    self.messages.append(message)
                # Use ANSI escape codes for coloring
                RESET = "\033[0m"
                TIME_COLOR = "\033[92m"  # Green for time
                USER_COLOR = "\033[94m"  # Blue for username
                SELF_COLOR = "\033[97m"  # White for self messages
                
                if message.username == self.username:
                    print(f"{TIME_COLOR}{message.time}{RESET} {USER_COLOR}[{message.username}]{RESET}: {SELF_COLOR}{message.message_content}{RESET}")
                else:
                    print(f"{TIME_COLOR}{message.time}{RESET} {USER_COLOR}[{message.username}]{RESET}: {message.message_content}")
            except socket.timeout:
                continue  # Timeout occurred, check running flag again
            except Exception as e:
                if self.running:
                    print(f"Error receiving message: {e}")
                break
        self.running = False
        if self.current_socket:
            self.current_socket.close()
            self.current_socket = None
            self.current_host = None

    def send_message(self, content: str) -> bool:
        """
        Send a message to the current host.
        Returns True if message is sent successfully or cached when offline, False otherwise.
        """
        if not self.current_socket or not self.running:
            print("Not connected to any host. Caching message.")
            self._cache_message(content)
            return True
        
        message_obj = Message(self.username, content)
        message = {
            "command_name": "MESSAGE",
            "username": self.username,
            "message_content": content,
            "time": message_obj.time
        }
        try:
            self.current_socket.send(json.dumps(message).encode("utf-8"))
            with self.messages_lock:
                self.messages.append(message_obj)
            return True
        except Exception as e:
            print(f"Error sending message: {e}")
            self.running = False
            self.current_socket.close()
            self.current_socket = None
            self.current_host = None
            self._cache_message(content)
            return True

    def disconnect(self):
        """Disconnect from the current host."""
        self.running = False
        if self.current_socket:
            try:
                self.current_socket.close()
            except Exception as e:
                print(f"Error closing socket: {e}")
            self.current_socket = None
            self.current_host = None
        # Small delay to ensure threads terminate
        time.sleep(0.1)
        print("Disconnected from host.")
        
    def _load_cached_messages(self):
        """Load cached messages from file."""
        try:
            with open(self.cached_messages_file, 'r') as f:
                self.cached_messages = json.load(f)
        except FileNotFoundError:
            self.cached_messages = []
        except Exception as e:
            print(f"Error loading cached messages: {e}")
            self.cached_messages = []
            
    def _cache_message(self, content: str):
        """Cache a message to be sent later when connection is available."""
        self.cached_messages.append(content)
        try:
            with open(self.cached_messages_file, 'w') as f:
                json.dump(self.cached_messages, f, indent=2)
        except Exception as e:
            print(f"Error caching message: {e}")
            
    def _send_cached_messages(self):
        """Send all cached messages to the current host."""
        if not self.cached_messages:
            return
            
        print(f"Sending {len(self.cached_messages)} cached messages...")
        remaining_messages = []
        for content in self.cached_messages:
            if not self.send_message(content):
                remaining_messages.append(content)
                
        self.cached_messages = remaining_messages
        try:
            with open(self.cached_messages_file, 'w') as f:
                json.dump(self.cached_messages, f, indent=2)
        except Exception as e:
            print(f"Error updating cached messages file: {e}")