import socket
import json
from threading import Thread, Lock
from utils.protocol import Command, Status, create_request, parse_response
import time

class PeerClient:
    def __init__(self, username, tracker_ip, tracker_port):
        # Tracker information
        self.tracker_ip = tracker_ip
        self.tracker_port = tracker_port
        
        # Peer client information
        self.username = username
        
        # Peer host information
        self.hosts = {}  # dictionary to store host information with (ip, port) as key
        self.sockets = {}  # dictionary to store sockets with (ip, port) as key
        self.running = {}  # Running status per host
        self.messages = {}  # Messages per host
        self.messages_lock = Lock()
        
        # 
        self.cached_messages = []
        self.cached_messages_file = f"{username}_cached_messages.json"
        self._load_cached_messages()

    # DONE
    def get_peer_hosts(self):
        """
        Send a request to the tracker to get the list of available peer hosts.
        Returns a list of dictionaries containing host information.
        """
        try:
            with socket.socket() as tracker_socket:
                tracker_socket.connect((self.tracker_ip, self.tracker_port))
                
                request = create_request(Command.LIST, {})
                tracker_socket.send(request)
                
                response = tracker_socket.recv(4096)
                status, payload = parse_response(response)
                
                if status == Status.OK.value:
                    return payload
                else:
                    print(f"Error from tracker: {status}")
                    return []
        except Exception as e:
            print(f"Error getting peer hosts from tracker: {e}")
            return []

    # DONE
    def connect_to_host(self, target_host):
        """
        Connect to a specific peer host to fetch and send messages.
        Returns True if connection is successful, False otherwise.
        """
        host_ip = target_host['peer_server_ip']
        host_port = target_host['peer_server_port']
        host_key = (host_ip, host_port)
        host_info = target_host.get('channel_name', 'Unknown Channel')
        try:
            # Prepare for new host connection
            new_socket = socket.socket()
            new_socket.connect(host_key)
            
            # Store host information
            self.sockets[host_key] = new_socket
            self.hosts[host_key] = host_info
            self.running[host_key] = True
            self.messages[host_key] = []
            
            # Receive initial messages
            data = new_socket.recv(4096)
            command, initial_messages = parse_response(data)
            
            if command != Command.MESSAGE.value:
                print(f"Unexpected command received: {command}")
                return False
            
            with self.messages_lock:
                for msg in initial_messages:
                    if isinstance(msg, dict) and 'username' in msg and 'message_content' in msg:
                        self.messages[host_key].append(msg)
                    else:
                        print(f"Warning: Invalid message format received: {msg}")
            
            # Start a thread to listen for new messages from this host
            Thread(target=self.listen_for_messages, args=(host_key,), daemon=True).start()
            print(f"Connected to host {host_ip}:{host_port}")
            
            # Send any cached messages to this host
            self._send_cached_messages(host_key)
            return True
        except Exception as e:
            print(f"Error connecting to host {host_ip}:{host_port}: {e}")
            if host_key in self.sockets:
                del self.sockets[host_key]
            if host_key in self.hosts:
                del self.hosts[host_key]
            return False

    # NOT DONE
    def listen_for_messages(self, host_key):
        """listen for incoming messages from a specific host."""
        host_ip, host_port = host_key
        socket_obj = self.sockets.get(host_key)
        if socket_obj:
            socket_obj.settimeout(1.0)
        while self.running.get(host_key, False) and socket_obj:
            try:
                data = socket_obj.recv(1024)
                if not data:
                    break
                try:
                    command, payload = parse_response(data)
                    if command == Command.MESSAGE.value:
                        message = payload
                    else:
                        continue  # Ignore non-message commands
                except ValueError:
                    # Fallback: Try to parse as raw JSON if protocol format fails
                    try:
                        message = json.loads(data)
                        if not isinstance(message, dict) or 'username' not in message or 'message_content' not in message:
                            print(f"Warning: Invalid message format received: {data}")
                            continue
                    except json.JSONDecodeError:
                        print(f"Error parsing message data: {data}")
                        continue
                with self.messages_lock:
                    self.messages[host_key].append(message)
                    
                RESET = "\033[0m"
                TIME_COLOR = "\033[92m"  # Green for time
                USER_COLOR = "\033[94m"  # Blue for username
                SELF_COLOR = "\033[97m"  # White for self messages
                if message['username'] == self.username:
                    print(f"{TIME_COLOR}{message['time']}{RESET} {SELF_COLOR}[{message['username']}]{RESET} {message['message_content']}")
                else:
                    print(f"{TIME_COLOR}{message['time']}{RESET} {USER_COLOR}[{message['username']}]{RESET} {message['message_content']}")
                
            except socket.timeout:
                continue  # Timeout occurred, check running flag again
            except Exception as e:
                if self.running.get(host_key, False):
                    print(f"Error receiving message from {host_ip}:{host_port}: {e}")
                break
        self.running[host_key] = False
        if host_key in self.sockets:
            self.sockets[host_key].close()
            del self.sockets[host_key]
        if host_key in self.hosts:
            del self.hosts[host_key]

    def send_message(self, content, host_key):
        """
        Send a message to a specific host or all connected hosts if host_key is None.
        Returns True if message is sent successfully to at least one host or cached when offline, False otherwise.
        """
        if not self.sockets or (host_key and host_key not in self.sockets):
            print("Not connected to the specified host or any host. Caching message.")
            self._cache_message(content)
            return True
        
        # Prepare message request
        payload = {
            "username": self.username,
            "message_content": content,
        }
        request = create_request(Command.MESSAGE, payload)
        success = False
        
        target_hosts = [host_key] if host_key else list(self.sockets.keys())
        for key in target_hosts:
            if key in self.sockets:
                try:
                    self.sockets[key].send(request)
                    with self.messages_lock:
                        self.messages[key].append(payload)
                    success = True
                    print(f"Message sent to {key[0]}:{key[1]}")
                except Exception as e:
                    print(f"Error sending message to {key[0]}:{key[1]}: {e}")
                    self.running[key] = False
                    self.sockets[key].close()
                    del self.sockets[key]
                    if key in self.hosts:
                        del self.hosts[key]
        
        if not success:
            print("Failed to send message to any host. Caching message.")
            self._cache_message(content)
        return True

    def disconnect(self, host_key):
        """Disconnect from a specific host or all hosts if host_key is None."""
        target_hosts = [host_key] if host_key else list(self.hosts.keys())
        for key in target_hosts:
            if key in self.running:
                self.running[key] = False
            if key in self.sockets:
                try:
                    self.sockets[key].close()
                except Exception as e:
                    print(f"Error closing socket for {key[0]}:{key[1]}: {e}")
                del self.sockets[key]
            if key in self.hosts:
                del self.hosts[key]
            print(f"Disconnected from host {key[0]}:{key[1]}")
        # Small delay to ensure threads terminate
        time.sleep(0.1)
        
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
            
    def _cache_message(self, content):
        """Cache a message to be sent later when connection is available."""
        self.cached_messages.append(content)
        try:
            with open(self.cached_messages_file, 'w') as f:
                json.dump(self.cached_messages, f, indent=2)
        except Exception as e:
            print(f"Error caching message: {e}")
            
    def _send_cached_messages(self, host_key):
        """Send all cached messages to a specific host or all connected hosts if host_key is None."""
        if not self.cached_messages:
            return
        
        print(f"Sending {len(self.cached_messages)} cached messages...")
        remaining_messages = []
        for content in self.cached_messages:
            if not self.send_message(content, host_key):
                remaining_messages.append(content)
                
        self.cached_messages = remaining_messages
        try:
            with open(self.cached_messages_file, 'w') as f:
                json.dump(self.cached_messages, f, indent=2)
        except Exception as e:
            print(f"Error updating cached messages file: {e}")