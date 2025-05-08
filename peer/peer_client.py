import socket
import json
from threading import Thread, Lock
from utils.protocol import Command, Status, create_request, parse
from utils.utils import print_message
import time
from uuid import uuid4
import queue
from utils.utils import UserType

class PeerClient:
    def __init__(self, username, tracker_ip, tracker_port):
        # Tracker information
        self.tracker_ip = tracker_ip
        self.tracker_port = tracker_port
        
        # Peer client information
        self.username = username
        self.user_type = UserType.GUEST  # Default user type
        self.invisible_mode = False  # Default visibility status
        
        # Peer host information using channel_name as key
        self.channels = {}  # Store channel information {channel_name: {ip, port, socket}}
        self.messages = {}  # Messages per channel {channel_name: [message1, message2, ...]}
        self.messages_lock = Lock()
        
        # Cached messages
        self.cached_messages = {}  # { channel_name: [message1, message2, ...] }
        self.cached_messages_file = f"{username}_cached_messages.json"
        self._load_cached_messages()
        print(f"Cached messages loaded: {self.cached_messages}")
        
        # Request tracking mechanism
        self.pending_responses = {}
        self.response_queues_lock = Lock()

    # OK
    def get_peer_hosts(self):
        try:
            with socket.socket() as tracker_socket:
                tracker_socket.connect((self.tracker_ip, self.tracker_port))
                
                # One time socket connection to tracker
                request = create_request(Command.LIST, {})
                tracker_socket.send(request)
                
                response = tracker_socket.recv(4096)
                status, payload, _ = parse(response)
                
                if status == Status.OK.value:
                    return payload
                else:
                    print(f"Error from tracker: {status}")
                    return []
                
        except Exception as e:
            print(f"Error getting peer hosts from tracker: {e}")
            return []
        finally:
            tracker_socket.close()

    # OK
    def connect_to_host(self, target_host):
        host_ip = target_host['peer_server_ip']
        host_port = target_host['peer_server_port']
        channel_name = target_host['channel_name']
        
        try:
            # Prepare for new host connection
            new_socket = socket.socket()
            new_socket.connect((host_ip, host_port))
            
            new_socket.send(create_request(Command.CONNECT, {
                "username": self.username,
                "user_type": self.user_type.value,
                "invisible": self.invisible_mode,
            }))
            
            response = new_socket.recv(1024)
            status, payload, _ = parse(response)
            
            if status == Status.OK.value:
                print(f"Connected to host: {status}")
                initial_messages = payload
            elif status == Status.UNAUTHORIZED.value:
                print(f"Error connecting to host: {status}")
                new_socket.close()
                return False
            else:
                print(f"Unexpected response from host: {status}")
                new_socket.close()
                return False
                        
            # Store connected channel information
            self.channels[channel_name] = {
                'ip': host_ip,
                'port': host_port,
                'socket': new_socket
            }
            
            # Load initial messages
            self.messages[channel_name] = []
            for msg in initial_messages:
                if isinstance(msg, dict) and 'username' in msg and 'message_content' in msg and 'time' in msg:
                    with self.messages_lock:
                        self.messages[channel_name].append(msg)
                else:
                    print(f"Warning: Invalid message format received: {msg}")
            
            # Start a thread to listen for new messages from this new channel
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
        
        # Already cleaned up in listen_for_messages

    # OK
    def listen_for_messages(self, channel_name):
        if channel_name not in self.channels:
            print(f"Error: Channel '{channel_name}' not found")
            return
        
        socket_obj = self.channels[channel_name]['socket']
        host_ip = self.channels[channel_name]['ip']
        host_port = self.channels[channel_name]['port']
        
        if socket_obj:
            socket_obj.settimeout(1.0)
        
        buffer = ""
        
        # To stop the thread when the channel is closed or disconnected
        while channel_name in self.channels and socket_obj:
            try:
                # Get data (may include multiple messages)
                data = socket_obj.recv(1024)
                if not data:
                    break

                buffer += data.decode("utf-8")
                while '\n' in buffer:
                    request, buffer = buffer.split('\n', 1)
                    if not request:
                        continue
                                        
                    try:
                        header, payload, id = parse(request, isSeparated=True)
                        print(f"[LOG] {header}-{payload}-{id}")
                        
                        # Response handling
                        if header in [
                            Status.OK.value,
                            Status.UNAUTHORIZED.value,
                            Status.REQUEST_ERROR.value,
                            Status.SERVER_ERROR.value,
                        ]:
                            with self.response_queues_lock:
                                if id in self.pending_responses:
                                    self.pending_responses[id].put(request)
                            continue
                        
                        # Request handling
                        elif header == Command.MESSAGE.value:
                            for msg in payload:
                                if isinstance(msg, dict) and 'username' in msg and 'message_content' in msg and 'time' in msg:
                                    with self.messages_lock:
                                        self.messages[channel_name].append(msg)
                                
                                '''Print out for debugging'''
                                print_message(msg, self.username)
                                
                    except ValueError:
                        print(f"Error parsing message: {request}")
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
            self.channels.pop(channel_name, "")
        print(f"Disconnected from channel '{channel_name}' at {host_ip}:{host_port}")

    # OK
    def send_message(self, content, channel_name):
        # Caching if not connected to the channel
        if not self.channels or (channel_name not in self.channels):
            print(f"Not connected to channel {channel_name}. Caching message.")
            self._cache_message(content, channel_name)
            return True
        
        # Send message and wait for response
        payload = {
            "username": self.username,
            "message_content": content,
        }
        status, payload = self.send_request_and_wait_response(
            self.channels[channel_name]['socket'],
            Command.MESSAGE,
            payload,
        )
        
        # Response handling
        if status == Status.OK.value:
            print(f"Message sent to channel '{channel_name}'")
            return True
        elif status == Status.UNAUTHORIZED.value:
            print(f"Unauthorized to send message to channel '{channel_name}'")
            return False
        elif status == Status.REQUEST_ERROR.value:
            print(f"Request error while sending message to channel '{channel_name}': {payload}")
            return False
        else:
            print(f"Unexpected response while sending message to channel '{channel_name}': {status}")
            return False
    
    def change_view(self, channel_name, view):
        """Change the view of messages for a specific channel."""
        if channel_name not in self.channels:
            print(f"Not connected to channel '{channel_name}'")
            return
        
        status, payload = self.send_request_and_wait_response(
            self.channels[channel_name]['socket'],
            Command.VIEW,
            {
                "username": self.username,
                "permission": view,
            },
        )
        
        if status == Status.OK.value:
            print(f"View changed to {bool(view)} for channel '{channel_name}'")
            return True
        elif status == Status.UNAUTHORIZED.value:
            print(f"Unauthorized to change view for channel '{channel_name}'")
            return False
        elif status == Status.REQUEST_ERROR.value:
            print(f"Request error while changing view for channel '{channel_name}': {payload}")
            return False
        else:
            print(f"Unexpected response while changing view for channel '{channel_name}': {status}")
            return False
    
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
        
    # NOT DONE, have to handle in listen_for_messages,...
    def disconnect(self, channel_name):
        if channel_name not in self.channels:
            print(f"Not connected to channel '{channel_name}'")
            return
        
        # Send disconnect request to the server (2 hướng: close socket or send disconnect request)
        try:
            self.channels[channel_name]['socket'].close()
        except Exception as e:
            print(f"Error closing socket for channel '{channel_name}': {e}")
            
        print(f"Disconnected from channel '{channel_name}'")
        
        # Change del to pop
        self.channels.pop(channel_name, "") 
        
        # Small delay to ensure threads terminate
        time.sleep(0.1)
        
    def retrieve_info(self, channel_name):
        """Retrieve information about the channel."""
        if channel_name not in self.channels:
            print(f"Not connected to channel '{channel_name}'")
            return
        
        status, payload = self.send_request_and_wait_response(
            self.channels[channel_name]['socket'],
            Command.RET_INFO,
            {
                "username": self.username,
            })
        
        if status == Status.OK.value:
            return payload
        elif status == Status.UNAUTHORIZED.value:
            print(payload['message'])
            return False
        elif status == Status.REQUEST_ERROR.value:
            print(payload['message'])
            return False
        else:
            print(f"Unexpected response while retrieving info for channel '{channel_name}': {status}")
            return False
    
    def set_invisible_mode(self, mode):
        """Set the visibility mode of the user."""
        if mode == "on":
            mode = True
        elif mode == "off":
            mode = False
        else:
            print("Invalid mode. Use 'on' or 'off'.")
            return
        
        if self.invisible_mode == mode:
            print(f"Visibility mode is already set to {mode}")
            return
        self.invisible_mode = mode
        print(f"client", self.invisible_mode)
        # Send request to all connected channels to update visibility
        for channel_name in self.channels:
            status, payload = self.send_request_and_wait_response(
                self.channels[channel_name]['socket'],
                Command.INVISIBLE,
                {
                    "username": self.username,
                    "invisible": mode,
                },
            )
            
            if status == Status.OK.value:
                print(f"Visibility set to {mode} for channel '{channel_name}'")
            elif status == Status.UNAUTHORIZED.value:
                print(payload['message'])
            elif status == Status.REQUEST_ERROR.value:
                print(payload['message'])
            else:
                print(f"Unexpected response while setting visibility for channel '{channel_name}': {status}")
        
    def authorize_user(self, channel_name, target, author_type):
        """Authorize a user to send messages in a specific channel."""
        if channel_name not in self.channels:
            print(f"Not connected to channel '{channel_name}'")
            return
        
        print("author", self.invisible_mode)
        status, payload = self.send_request_and_wait_response(
            self.channels[channel_name]['socket'],
            Command.AUTHORIZE,
            {
                "actor": self.username,
                "target": target,
                "author_type": author_type,
            },
        )
        
        if status == Status.OK.value:
            print(f"User '{target}' authorized in channel '{channel_name}'")
            return True
        elif status == Status.UNAUTHORIZED.value:
            print(payload['message'])
            return False
        elif status == Status.REQUEST_ERROR.value:
            print(payload['message'])
            return False

    # OK
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

    # OK
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
    
    # OK
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
                
            status, payload = self.send_request_and_wait_response(
                self.channels[channel_name]['socket'],
                Command.MESSAGE,
                payload,
            )
            
            # Response handling
            if status == Status.OK.value:
                print(f"Message sent to channel '{channel_name}'")
                # Save updated cache to file
                try:
                    if channel_name in self.cached_messages:
                        del self.cached_messages[channel_name]
                    with open(self.cached_messages_file, 'w') as f:
                        json.dump(self.cached_messages, f, indent=2)
                except Exception as e:
                    print(f"Error updating cached messages file: {e}")
                return True
            
            elif status == Status.UNAUTHORIZED.value:
                print(f"Unauthorized to send message to channel '{channel_name}'")
                return False
            elif status == Status.REQUEST_ERROR.value:
                print(f"Request error while sending message to channel '{channel_name}': {payload}")
                return False
            else:
                print(f"Unexpected response while sending message to channel '{channel_name}': {status}")
                return False

    # OK
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
                status, payload, _ = parse(response, isSeparated=True)
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
                    
    '''
    TRACKER INTERACTION METHODS
    '''
    def signup(self, username, password):
        with socket.socket() as tracker_socket:
            tracker_socket.connect((self.tracker_ip, self.tracker_port))
            
            # One time socket connection to tracker
            request = create_request(Command.SIGNUP, {
                "username": username,
                "password": password,
            })
            tracker_socket.send(request)
            
            response = tracker_socket.recv(4096)
            status, payload, _ = parse(response)
            
            if status == Status.OK.value:
                print(f"{payload['message']}")
                self.username = username
                self.user_type = UserType.REGISTERED
                return True

            elif status == Status.REQUEST_ERROR.value:
                print(f"Request error while signing up: {payload['message']}")
                return False
            
    def signin(self, username, password):
        with socket.socket() as tracker_socket:
            tracker_socket.connect((self.tracker_ip, self.tracker_port))
            
            # One time socket connection to tracker
            request = create_request(Command.SIGNIN, {
                "username": username,
                "password": password,
            })
            tracker_socket.send(request)
            
            response = tracker_socket.recv(4096)
            status, payload, _ = parse(response)
            
            if status == Status.OK.value:
                print(f"{payload['message']}")
                self.username = username
                self.user_type = UserType.REGISTERED
                return True

            elif status == Status.REQUEST_ERROR.value:
                print(f"Request error while logging in: {payload['message']}")
                return False