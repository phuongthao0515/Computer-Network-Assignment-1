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
        channel_name = target_host['channel_name']
        
        try:
            # Prepare for new host connection
            new_socket = socket.socket()
            new_socket.connect((host_ip, host_port))
            
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
        
        buffer = ""
        while channel_name in self.channels and socket_obj:
            try:
                data = socket_obj.recv(1024)
                if not data:
                    break
                
                buffer += data.decode("utf-8")
                while '\\' in buffer:
                    # Split the buffer into individual requests
                    request, buffer = buffer.split('\\', 1)
                    
                    if not request:
                        continue
                    
                    # Parse the request
                    try:
                        command, payload = parse_response(request, isSeparated=True)
                        if command == Command.MESSAGE.value:
                            messages = payload
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
                            
                        elif command == Status.UNAUTHORIZED.value:
                            print(f"Unauthorized access to channel '{channel_name}'")
                            continue  # Ignore non-message commands
                    except ValueError:
                        # Fallback: Try to parse as raw JSON if protocol format fails
                        try:
                            message = json.loads(request)
                            if not isinstance(message, dict) or 'username' not in message or 'message_content' not in message:
                                print(f"Warning: Invalid message format received: {request}")
                                continue
                        except json.JSONDecodeError:
                            print(f"Error parsing message data: {request}")
                            continue
                
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
            return True
        
        # Prepare message request
        payload = {
            "username": self.username,
            "message_content": content,
        }
        request = create_request(Command.MESSAGE, payload)
        success = False
        
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
    
    def debug(self, channel_name):
        """Send a debug command to a specific channel."""
        if channel_name not in self.channels:
            print(f"Not connected to channel '{channel_name}'")
            return
        
        request = create_request(Command.DEBUG, {})
        try:
            self.channels[channel_name]['socket'].send(request)            
            print(f"Debug command sent to channel '{channel_name}'")
        except Exception as e:
            print(f"Error sending debug command to channel '{channel_name}': {e}")
        

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

    def _load_cached_messages(self):
        """Load cached messages from file."""
        try:
            with open(self.cached_messages_file, 'r') as f:
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