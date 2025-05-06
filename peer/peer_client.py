import socket
import json
from threading import Thread, Lock
from utils.protocol import Command, Status, create_request, parse_response
import time

class PeerClient:
<<<<<<< HEAD
    def __init__(self, username: str, tracker_ip: str, tracker_port: int):
=======
    def __init__(self, username, tracker_ip, tracker_port):
>>>>>>> a3c6e008a6135d7897cffa802128250c860b1650
        # Tracker information
        self.tracker_ip = tracker_ip
        self.tracker_port = tracker_port
        
        # Peer client information
        self.username = username
        
<<<<<<< HEAD
        # Peer host information
        self.hosts = {}  # dictionary to store host information with (ip, port) as key
        self.sockets = {}  # dictionary to store sockets with (ip, port) as key
        
        # Messages information
        self.messages: dict[tuple[str, int], list[dict[str, str]]] = {}  # Messages per host
        self.messages_lock = Lock()
        self.running = {}  # Running status per host
        self.cached_messages: list[str] = []
        self.cached_messages_file = f"{username}_cached_messages.json"
        self._load_cached_messages()

    # DONE
    def get_peer_hosts(self) -> list[dict]:
=======
        # Peer host information using channel_name as key
        self.channels = {}  # Store channel information {channel_name: {ip, port, socket}}
        self.messages = {}  # Messages per channel {channel_name: [message1, message2, ...]}
        self.messages_lock = Lock()
        
        # Cached messages
        self.cached_messages = {}  # { channel_name: [message1, message2, ...] }
        self.cached_messages_file = f"{username}_cached_messages.json"
        self._load_cached_messages()
        print(f"Cached messages loaded: {self.cached_messages}")

    # DONE
    def get_peer_hosts(self):
>>>>>>> a3c6e008a6135d7897cffa802128250c860b1650
        """
        Send a request to the tracker to get the list of available peer hosts.
        Returns a list of dictionaries containing host information.
        """
        try:
            with socket.socket() as tracker_socket:
                tracker_socket.connect((self.tracker_ip, self.tracker_port))
                
                request = create_request(Command.LIST, {})
<<<<<<< HEAD
                tracker_socket.send(request.encode("utf-8"))
                
                response = tracker_socket.recv(4096).decode("utf-8")
=======
                tracker_socket.send(request)
                
                response = tracker_socket.recv(4096)
>>>>>>> a3c6e008a6135d7897cffa802128250c860b1650
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
<<<<<<< HEAD
    def connect_to_host(self, host_ip: str, host_port: int) -> bool:
=======
    def connect_to_host(self, target_host):
>>>>>>> a3c6e008a6135d7897cffa802128250c860b1650
        """
        Connect to a specific peer host to fetch and send messages.
        Returns True if connection is successful, False otherwise.
        """
<<<<<<< HEAD
        host_key = (host_ip, host_port)
=======
        host_ip = target_host['peer_server_ip']
        host_port = target_host['peer_server_port']
        channel_name = target_host['channel_name']
        
>>>>>>> a3c6e008a6135d7897cffa802128250c860b1650
        try:
            # Prepare for new host connection
            new_socket = socket.socket()
            new_socket.connect((host_ip, host_port))
<<<<<<< HEAD
            self.sockets[host_key] = new_socket
            self.hosts[host_key] = host_key
            self.running[host_key] = True
            self.messages[host_key] = []
            
            # Receive initial messages
            data = new_socket.recv(4096).decode("utf-8")
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
    def listen_for_messages(self, host_key: tuple[str, int]):
        """listen for incoming messages from a specific host."""
        host_ip, host_port = host_key
        socket_obj = self.sockets.get(host_key)
        if socket_obj:
            socket_obj.settimeout(1.0)
        while self.running.get(host_key, False) and socket_obj:
            try:
                data = socket_obj.recv(1024).decode("utf-8")
=======
            
            # Store channel information
            self.channels[channel_name] = {
                'ip': host_ip,
                'port': host_port,
                'socket': new_socket
            }
            self.messages[channel_name] = []
            
            # receive initial messages
            response = new_socket.recv(4096)
            command, initial_messages = parse_response(response)
            if command != Command.MESSAGE.value:
                print(f"Unexpected command received: {command}")
                return False
            for msg in initial_messages:
                if isinstance(msg, dict) and 'username' in msg and 'message_content' in msg and 'time' in msg:
                    with self.messages_lock:
                        self.messages[channel_name].append(msg)
                else:
                    print(f"Warning: Invalid message format received: {msg}")
            
            # Start a thread to listen for new messages from this channel
            Thread(target=self.listen_for_messages, args=(channel_name,), daemon=True).start()
            print(f"Connected to channel '{channel_name}' at {host_ip}:{host_port}")
                                    
            return True
        except Exception as e:
            print(f"Error connecting to channel '{channel_name}' at {host_ip}:{host_port}: {e}")
            if channel_name in self.channels:
                del self.channels[channel_name]
            if channel_name in self.messages:
                del self.messages[channel_name]
            return False

    def listen_for_messages(self, channel_name):
        """Listen for incoming messages from a specific channel."""
        if channel_name not in self.channels:
            print(f"Error: Channel '{channel_name}' not found")
            return
        
        channel_info = self.channels[channel_name]
        socket_obj = channel_info['socket']
        host_ip = channel_info['ip']
        host_port = channel_info['port']
        
        if socket_obj:
            socket_obj.settimeout(1.0)
            
        while channel_name in self.channels and socket_obj:
            try:
                data = socket_obj.recv(1024)
>>>>>>> a3c6e008a6135d7897cffa802128250c860b1650
                if not data:
                    break
                try:
                    command, payload = parse_response(data)
                    if command == Command.MESSAGE.value:
<<<<<<< HEAD
                        message = payload
=======
                        messages = payload
>>>>>>> a3c6e008a6135d7897cffa802128250c860b1650
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
<<<<<<< HEAD
                with self.messages_lock:
                    self.messages[host_key].append(message)
                
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

    def send_message(self, content: str, host_key: tuple[str, int] = None) -> bool:
        """
        Send a message to a specific host or all connected hosts if host_key is None.
        Returns True if message is sent successfully to at least one host or cached when offline, False otherwise.
        """
        if not self.sockets or (host_key and host_key not in self.sockets):
            print("Not connected to the specified host or any host. Caching message.")
            self._cache_message(content)
=======
                
                for msg in messages:
                    with self.messages_lock:
                        self.messages[channel_name].append(msg)
                    
                    RESET = "\033[0m"
                    TIME_COLOR = "\033[92m"  # Green for time
                    USER_COLOR = "\033[94m"  # Blue for username
                    SELF_COLOR = "\033[97m"  # White for self messages
                    if msg['username'] == self.username:
                        print(f"{TIME_COLOR}{msg['time']}{RESET} {SELF_COLOR}[{msg['username']}]{RESET}: {msg['message_content']}")
                    else:
                        print(f"{TIME_COLOR}{msg['time']}{RESET} {USER_COLOR}[{msg['username']}]{RESET}: {msg['message_content']}")
                
            except socket.timeout:
                continue  # Timeout occurred, check if channel still exists
            except socket.error as e:
                if channel_name in self.channels:
                    print(f"Connection to channel '{channel_name}' at {host_ip}:{host_port} was closed: {e}")
                break
            except Exception as e:
                print(f"Error receiving message from channel '{channel_name}' at {host_ip}:{host_port}: {e}")
                break
        
        # Cleanup on disconnection
        if channel_name in self.channels:
            if self.channels[channel_name]['socket']:
                self.channels[channel_name]['socket'].close()
            del self.channels[channel_name]
        print(f"Disconnected from channel '{channel_name}' at {host_ip}:{host_port}")

    def send_message(self, content, channel_name=None):
        """
        Send a message to a specific channel or all connected channels if channel_name is None.
        Returns True if message is sent successfully to at least one channel or cached when offline, False otherwise.
        """
        if not self.channels or (channel_name and channel_name not in self.channels):
            print("Not connected to the specified channel or any channel. Caching message.")
            # Cache message for specified channel or all known channels
            if channel_name:
                self._cache_message(content, channel_name)
            else:
                if self.channels:
                    for ch_name in self.channels.keys():
                        self._cache_message(content, ch_name)
                else:
                    # No specific channel, cache as general message
                    self._cache_message(content, None)
>>>>>>> a3c6e008a6135d7897cffa802128250c860b1650
            return True
        
        # Prepare message request
        payload = {
            "username": self.username,
            "message_content": content,
        }
        request = create_request(Command.MESSAGE, payload)
        success = False
        
<<<<<<< HEAD
        target_hosts = [host_key] if host_key else list(self.sockets.keys())
        for key in target_hosts:
            if key in self.sockets:
                try:
                    self.sockets[key].send(request.encode("utf-8"))
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

    def disconnect(self, host_key: tuple[str, int] = None):
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
        
=======
        target_channels = [channel_name] if channel_name else list(self.channels.keys())
        for ch_name in target_channels:
            if ch_name in self.channels:
                try:
                    self.channels[ch_name]['socket'].send(request)
                    with self.messages_lock:
                        self.messages[ch_name].append(payload)
                    success = True
                    print(f"Message sent to channel '{ch_name}'")
                except Exception as e:
                    print(f"Error sending message to channel '{ch_name}': {e}")
                    if ch_name in self.channels:
                        self.channels[ch_name]['socket'].close()
                        del self.channels[ch_name]
                    # Cache the message for this specific channel
                    self._cache_message(content, ch_name)
        
        if not success and not channel_name:
            print("Failed to send message to any channel. Caching message for all known channels.")
            if self.channels:
                for ch_name in self.channels.keys():
                    self._cache_message(content, ch_name)
            else:
                # No specific channel, cache as general message
                self._cache_message(content, None)
        return True

    def disconnect(self, channel_name=None):
        """Disconnect from a specific channel or all channels if channel_name is None."""
        target_channels = [channel_name] if channel_name else list(self.channels.keys())
        for ch_name in target_channels:
            if ch_name in self.channels:
                try:
                    self.channels[ch_name]['socket'].close()
                except Exception as e:
                    print(f"Error closing socket for channel '{ch_name}': {e}")
                print(f"Disconnected from channel '{ch_name}'")
                del self.channels[ch_name]
        
        # Small delay to ensure threads terminate
        time.sleep(0.1)

>>>>>>> a3c6e008a6135d7897cffa802128250c860b1650
    def _load_cached_messages(self):
        """Load cached messages from file."""
        try:
            with open(self.cached_messages_file, 'r') as f:
<<<<<<< HEAD
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
            
    def _send_cached_messages(self, host_key: tuple[str, int] = None):
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
=======
                channel_name_with_cached_messages = json.load(f)
                # Iterate through the cached messages and add them to the cache
                for channel_name, messages in channel_name_with_cached_messages.items():
                    if channel_name not in self.cached_messages:
                        self.cached_messages[channel_name] = []
                    self.cached_messages[channel_name].extend(messages)
        except FileNotFoundError:
            self.cached_messages = {}
        except Exception as e:
            print(f"Error loading cached messages: {e}")
            self.cached_messages = {}
            
    def _cache_message(self, message_content, channel_name):
        """
        Cache a message to be sent later when connection is available.
        
        Args:
            message_content: The message content to cache
            channel_name: The name of the channel
        """
        # Initialize list for this channel if it doesn't exist
        if channel_name not in self.cached_messages:
            self.cached_messages[channel_name] = []
        
        # Add the message to the channel's list
        self.cached_messages[channel_name].append(message_content)
        
        try:
            with open(self.cached_messages_file, 'w') as f:
                json.dump(self.cached_messages, f, indent=4)
        except Exception as e:
            print(f"Error caching message: {e}")
    
    # DONE
    def _send_cached_messages(self, channel_name):
        """
        Send cached messages intended for the specified channel.
        
        Args:
            channel_name: The name of the channel to send cached messages to
        """
        if not self.cached_messages:
            return
        
        # Check if we have any messages for this channel
        messages_to_send = self.cached_messages.get(channel_name, [])
        
        if messages_to_send:
            print(f"Sending {len(messages_to_send)} cached messages to channel '{channel_name}'...")

            # Prepare the payload for sending multiple messages at once
            payload = [{
                "username": self.username,
                "message_content": msg,
            } for msg in messages_to_send]
                
            request = create_request(Command.CACHE, payload)
            self.channels[channel_name]['socket'].send(request)
            # No response needed for cache command
            
            # Save updated cache to file
            try:
                del self.cached_messages[channel_name]  # Remove sent messages from cache
                # Save the updated cached messages to file
                with open(self.cached_messages_file, 'w') as f:
                    json.dump(self.cached_messages, f, indent=2)
            except Exception as e:
                print(f"Error updating cached messages file: {e}")
>>>>>>> a3c6e008a6135d7897cffa802128250c860b1650
