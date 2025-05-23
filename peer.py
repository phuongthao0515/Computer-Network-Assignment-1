import argparse
import random
from peer.peer_host import PeerHost
from peer.peer_client import PeerClient
from threading import Thread
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import time
from datetime import datetime


######################## 
#   GUI section
########################

class Page(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.configure(bg="#f0f0f0")

# Login Page
class LoginPage(Page):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        
        # Create a styled frame for login and signup
        login_frame = tk.Frame(self, bg="#f0f0f0", bd=2, relief=tk.RAISED, padx=20, pady=20)
        login_frame.place(relx=0.5, rely=0.45, anchor=tk.CENTER)
        
        # Title
        title_label = tk.Label(login_frame, text="Peer Chat", font=("Arial", 24, "bold"), bg="#f0f0f0")
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 20))
        
        # Username for login/signup
        username_label = tk.Label(login_frame, text="Username:", font=("Arial", 12), bg="#f0f0f0")
        username_label.grid(row=1, column=0, sticky=tk.W, pady=(0, 10))
        
        self.username_entry = tk.Entry(login_frame, font=("Arial", 12), width=25)
        self.username_entry.grid(row=1, column=1, pady=(0, 10))
        self.username_entry.insert(0, "User")
        
        # Password (optional)
        password_label = tk.Label(login_frame, text="Password:", font=("Arial", 12), bg="#f0f0f0")
        password_label.grid(row=2, column=0, sticky=tk.W, pady=(0, 20))
        
        self.password_entry = tk.Entry(login_frame, font=("Arial", 12), width=25, show="*")
        self.password_entry.grid(row=2, column=1, pady=(0, 20))
        
        # Login and Sign Up buttons
        action_frame = tk.Frame(login_frame, bg="#f0f0f0")
        action_frame.grid(row=3, column=0, columnspan=2)
        
        login_button = tk.Button(action_frame, text="Login", font=("Arial", 12, "bold"),
                                 bg="#4CAF50", fg="white", width=10,
                                 command=self.login)
        login_button.grid(row=0, column=0, padx=5)

        signup_button = tk.Button(action_frame, text="Sign Up", font=("Arial", 12, "bold"),
                                  bg="#2196F3", fg="white", width=10,
                                  command=self.signup)
        signup_button.grid(row=0, column=1, padx=5)
        
        # Guest join container below with separate username entry
        guest_frame = tk.Frame(self, bg="#f0f0f0", bd=2, relief=tk.RIDGE, padx=15, pady=15)
        guest_frame.place(relx=0.5, rely=0.75, anchor=tk.CENTER)
        
        guest_title = tk.Label(guest_frame, text="Join as Guest", font=("Arial", 14, "bold"), bg="#f0f0f0")
        guest_title.grid(row=0, column=0, columnspan=2, pady=(0, 10))

        guest_label = tk.Label(guest_frame, text="Guest Username:", font=("Arial", 12), bg="#f0f0f0")
        guest_label.grid(row=1, column=0, sticky=tk.W, pady=(0, 10))
        
        self.guest_username_entry = tk.Entry(guest_frame, font=("Arial", 12), width=25)
        self.guest_username_entry.grid(row=1, column=1, pady=(0, 10))
        self.guest_username_entry.insert(0, "GuestUser")
        
        guest_button = tk.Button(guest_frame, text="Enter as Guest", font=("Arial", 12, "bold"),
                                 bg="#FF9800", fg="white", width=15,
                                 command=self.join_as_guest)
        guest_button.grid(row=2, column=0, columnspan=2)

    def _validate_username(self, username):
        if not username:
            messagebox.showerror("Error", "Username cannot be empty")
            return False
        return True

    def login(self):
        username = self.username_entry.get().strip()
        if not self._validate_username(username):
            return
        self.controller.client.username = username
        self.controller.username = username
        self.controller.show_frame(ChannelListPage)
        self.controller.frames[ChannelListPage].load_channels()

    def signup(self):
        username = self.username_entry.get().strip()
        if not self._validate_username(username):
            return
        messagebox.showinfo("Success", f"Account created for '{username}'!")

        self.controller.client.username = username
        self.controller.username = username
        self.controller.show_frame(ChannelListPage)
        self.controller.frames[ChannelListPage].load_channels()

    def join_as_guest(self):
        guest_name = self.guest_username_entry.get().strip()
        if not self._validate_username(guest_name):
            return
        guest_full = f"Guest_{guest_name}"
        self.controller.client.username = guest_full
        self.controller.username = guest_full
        messagebox.showinfo("Guest Mode", f"You are now joined as guest: '{guest_full}'")
        self.controller.show_frame(ChannelListPage)
        self.controller.frames[ChannelListPage].load_channels()

# Channel Selection Page
class ChannelListPage(Page):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        
        # Main container
        self.main_container = tk.Frame(self, bg="#f0f0f0")
        self.main_container.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Title
        title_label = tk.Label(self.main_container, text="Channel List", font=("Arial", 24, "bold"), bg="#f0f0f0")
        title_label.pack(pady=(0, 20))
        
        # Username display
        self.username_label = tk.Label(self.main_container, text="Logged in as: User", font=("Arial", 12), bg="#f0f0f0")
        self.username_label.pack(pady=(0, 20))
        
        # Add a refresh button
        refresh_button = tk.Button(self.main_container, text="Refresh Channels", 
                                  command=self.load_channels, bg="#3498db", fg="white", font=("Arial", 10))
        refresh_button.pack(pady=(0, 10))
        
        # Create two frames for channels: available and joined
        channels_container = tk.Frame(self.main_container, bg="#f0f0f0")
        channels_container.pack(fill="both", expand=True)

        # --- Available channels scrollable setup ---
        available_frame = tk.LabelFrame(channels_container, text="Available Channels", font=("Arial", 12, "bold"), 
                                    bg="#f0f0f0", padx=10, pady=10)
        available_frame.pack(side=tk.LEFT, fill="both", expand=True, padx=(0, 10))

        # Canvas + Scrollbar
        avail_canvas = tk.Canvas(available_frame, bg="#f0f0f0", highlightthickness=0)
        avail_scroll = tk.Scrollbar(available_frame, orient="vertical", command=avail_canvas.yview)
        avail_canvas.configure(yscrollcommand=avail_scroll.set)

        avail_scroll.pack(side="right", fill="y")
        avail_canvas.pack(side="left", fill="both", expand=True)

        # This is the interior frame that you’ll actually pack your widgets into:
        self.available_channels_container = tk.Frame(avail_canvas, bg="#f0f0f0")
        # Put it into the canvas
        avail_canvas.create_window((0,0), window=self.available_channels_container, anchor="nw")

        # Keep the scroll region in sync with the frame’s size:
        def _on_avail_configure(event):
            avail_canvas.configure(scrollregion=avail_canvas.bbox("all"))
        self.available_channels_container.bind("<Configure>", _on_avail_configure)


        # --- Joined channels scrollable setup ---
        joined_frame = tk.LabelFrame(channels_container, text="Joined Channels", font=("Arial", 12, "bold"), 
                                    bg="#f0f0f0", padx=10, pady=10)
        joined_frame.pack(side=tk.RIGHT, fill="both", expand=True, padx=(10, 0))

        join_canvas = tk.Canvas(joined_frame, bg="#f0f0f0", highlightthickness=0)
        join_scroll = tk.Scrollbar(joined_frame, orient="vertical", command=join_canvas.yview)
        join_canvas.configure(yscrollcommand=join_scroll.set)

        join_scroll.pack(side="right", fill="y")
        join_canvas.pack(side="left", fill="both", expand=True)

        self.joined_channels_container = tk.Frame(join_canvas, bg="#f0f0f0")
        join_canvas.create_window((0,0), window=self.joined_channels_container, anchor="nw")

        def _on_join_configure(event):
            join_canvas.configure(scrollregion=join_canvas.bbox("all"))
        self.joined_channels_container.bind("<Configure>", _on_join_configure)
                
        # Open Chat button
        open_chat_button = tk.Button(self.main_container, text="Open Chat", font=("Arial", 12, "bold"), 
                                   bg="#4CAF50", fg="white", command=self.open_chat)
        open_chat_button.pack(pady=20)
        
        # Logout button
        logout_button = tk.Button(self.main_container, text="Logout", font=("Arial", 10), 
                                 command=self.logout, bg="#e74c3c", fg="white")
        logout_button.pack(pady=(0, 10))
    
    def load_channels(self):
        # Update username display
        self.username_label.config(text=f"Logged in as: {self.controller.username}")
        
        # Clear existing channels
        for child in self.available_channels_container.winfo_children():
            child.destroy()
        for child in self.joined_channels_container.winfo_children():
            child.destroy()
        
        # Get all available channels
        channels = getAllChannel()
        print(channels)
        
        # Get connected channels
        connected_channels = getAllConnectedChannel()
        print(connected_channels)
        
        # Display available channels
        if not channels:
            tk.Label(self.available_channels_container, text="No channels found", bg="#f0f0f0").pack()
        else:
            for ch in channels:
                channel_name = ch.get("channel_name")
                host_key = (ch.get('peer_server_ip'), ch.get('peer_server_port'))
                
                # Skip if this channel is already connected
                if host_key in connected_channels:
                    continue
                    
                channel_frame = tk.Frame(self.available_channels_container, bg="#f0f0f0", pady=5)
                channel_frame.pack(fill="x", expand=True)
                
                channel_label = tk.Label(channel_frame, text=channel_name, bg="#f0f0f0", font=("Arial", 11))
                channel_label.pack(side=tk.LEFT, padx=(5, 0))
                
                join_btn = tk.Button(
                    channel_frame, 
                    text="Join", 
                    bg="#3498db", 
                    fg="white",
                    command=lambda c=ch: self.join_channel(c)
                )
                join_btn.pack(side=tk.RIGHT, padx=(0, 5))
        
        # Display joined channels
        if not connected_channels:
            tk.Label(self.joined_channels_container, text="Not connected to any channels", bg="#f0f0f0").pack()
        else:
            for host_key in connected_channels:
                channel_name = host_key.get("channel_name")
                
                channel_frame = tk.Frame(self.joined_channels_container, bg="#f0f0f0", pady=5)
                channel_frame.pack(fill="x", expand=True)
                
                channel_label = tk.Label(channel_frame, text=channel_name, bg="#f0f0f0", font=("Arial", 11))
                channel_label.pack(side=tk.LEFT, padx=(5, 0))
                
                disconnect_btn = tk.Button(
                    channel_frame, 
                    text="Disconnect", 
                    bg="#e74c3c", 
                    fg="white",
                    command=lambda name=channel_name: self.disconnect_channel(name)
                )
                disconnect_btn.pack(side=tk.RIGHT, padx=(0, 5))
    
    def join_channel(self, channel):
        channel_name = channel.get("channel_name")
        host_ip = channel.get("peer_server_ip")
        host_port = channel.get("peer_server_port")
        
        success = joinChannel(channel_name)
        if success:
            messagebox.showinfo("Success", f"Joined channel: {channel_name}")
            self.load_channels()
        else:
            messagebox.showerror("Error", f"Failed to join channel: {channel_name}")
    
    def disconnect_channel(self, channel_name):
        result = disconectChannel(channel_name)
        if result == "Success":
            messagebox.showinfo("Success", f"Disconnected from channel: {channel_name}")
        else:
            messagebox.showerror("Error", result)
        self.load_channels()
    
    def open_chat(self):
        connected = getAllConnectedChannel()
        if not connected:
            messagebox.showinfo("Info", "Please join at least one channel before opening chat.")
            return
        
        # Move to the messaging page
        self.controller.show_frame(MessagingPage)
        # Initialize the messaging page
        self.controller.frames[MessagingPage].initialize_chat()
    
    def logout(self):
        # Disconnect from all channels
        for channel in getAllConnectedChannel():
            print(channel)
            self.controller.client.disconnect(channel['channel_name'])
        # Reset username
        self.controller.username = "User"
        # Go back to login page
        self.controller.show_frame(LoginPage)

# Chat Page
class MessagingPage(Page):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.current_channel = None
        
        # Create a main container with split view
        self.main_container = tk.PanedWindow(self, orient=tk.HORIZONTAL, bg="#f0f0f0", sashwidth=5)
        self.main_container.pack(fill="both", expand=True)
        
        # Channels sidebar
        self.sidebar = tk.Frame(self.main_container, bg="#2c3e50", width=200)
        self.main_container.add(self.sidebar, width=200)
        
        # Channels title
        sidebar_title = tk.Label(self.sidebar, text="Channels", font=("Arial", 16, "bold"), 
                               bg="#2c3e50", fg="white", pady=10)
        sidebar_title.pack(fill="x")
        
        # Scrollable channel list
        self.channels_container = tk.Frame(self.sidebar, bg="#2c3e50")
        self.channels_container.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Back button in sidebar
        back_button = tk.Button(self.sidebar, text="Back to Channels", font=("Arial", 10), 
                              command=lambda: controller.show_frame(ChannelListPage), bg="#34495e", fg="white")
        back_button.pack(fill="x", padx=5, pady=10)
        
        # Chat area
        self.chat_area = tk.Frame(self.main_container, bg="#f0f0f0")
        self.main_container.add(self.chat_area, width=600)
        
        # Chat header with channel name
        self.chat_header = tk.Frame(self.chat_area, bg="#3498db", height=50)
        self.chat_header.pack(fill="x")
        
        self.channel_name_label = tk.Label(self.chat_header, text="Select a Channel", 
                                         font=("Arial", 14, "bold"), bg="#3498db", fg="white", padx=10, pady=10)
        self.channel_name_label.pack(side=tk.LEFT)

        # Manual refresh button
        self.refresh_button = tk.Button(
            self.chat_header,
            text="🔄",  # or "Refresh"
            font=("Arial", 10),
            bg="#2980b9",
            fg="white",
            relief=tk.FLAT,
            command=self.manual_refresh
        )
        self.refresh_button.pack(side=tk.LEFT, padx=5)
        
        # Chat messages
        self.messages_frame = tk.Frame(self.chat_area, bg="#f0f0f0")
        self.messages_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.chat_display = scrolledtext.ScrolledText(self.messages_frame, wrap=tk.WORD, 
                                                   font=("Arial", 11), bg="white", height=20)
        self.chat_display.pack(fill="both", expand=True)
        self.chat_display.config(state=tk.DISABLED)
        
        # Message input area
        self.input_frame = tk.Frame(self.chat_area, bg="#f0f0f0", pady=10)
        self.input_frame.pack(fill="x", side=tk.BOTTOM, padx=10, pady=10)
        
        self.message_entry = tk.Entry(self.input_frame, font=("Arial", 12))
        self.message_entry.pack(side=tk.LEFT, fill="x", expand=True, padx=(0, 10))
        self.message_entry.bind("<Return>", self.send_message)
        
        self.send_button = tk.Button(self.input_frame, text="Send", font=("Arial", 12), 
                                   bg="#2ecc71", fg="white", command=self.send_message)
        self.send_button.pack(side=tk.RIGHT)
    
    def initialize_chat(self):
        # Clear channel list
        for widget in self.channels_container.winfo_children():
            widget.destroy()
        
        # Get connected channels
        connected_channels = getAllConnectedChannel()
        
        if not connected_channels:
            # Display message if no channels are connected
            no_channels_label = tk.Label(self.channels_container, text="No channels joined", 
                                       bg="#2c3e50", fg="white", pady=5)
            no_channels_label.pack(fill="x")
            return
        
        # Create channel buttons
        for channel in connected_channels:
            channel_name = channel.get("channel_name")
            
            # Create a styled button for each channel
            channel_btn = tk.Button(
                self.channels_container,
                text=channel_name,
                font=("Arial", 11),
                bg="#34495e",
                fg="white",
                bd=0,
                pady=8,
                anchor="w",
                command=lambda c=channel_name : self.select_channel(c)
            )
            channel_btn.pack(fill="x", pady=2)
        
        # Select the first channel by default
        print("Connected: ", connected_channels)
        first_channel = list(connected_channels)[0]
        first_channel_name = first_channel.get("channel_name")
        self.select_channel(first_channel_name)
        
        # Start message update timer
        self.update_messages()
    
    def select_channel(self, channel_name):
        print("Initiate select channel")
        self.current_channel = channel_name
        self.channel_name_label.config(text=channel_name)
        
        # Load messages for this channel
        self.load_channel_messages(channel_name)
    
    def load_channel_messages(self, channel_name):
        print("Run load channel")
        self.chat_display.config(state=tk.NORMAL)
        self.chat_display.delete(1.0, tk.END)
        
        # Get messages for this channel
        messages = getMessage(channel_name)
        print("Channel Name: ", channel_name)
        print(messages)
        
        for msg in messages:
            # TODO
            time_str = datetime.now().strftime("%H:%M:%S")
            if 'time' in msg:
                time_str = msg['time']
            
            username = msg.get('username', 'Unknown')
            content = msg.get('message_content', '')
            
            # Format: [time] [username]: message
            if username == self.controller.username:
                # Style own messages differently
                self.chat_display.insert(tk.END, f"[{time_str}] ", "time")
                self.chat_display.insert(tk.END, f"[{username}]: ", "self_user")
                self.chat_display.insert(tk.END, f"{content}\n", "self_msg")
            else:
                self.chat_display.insert(tk.END, f"[{time_str}] ", "time")
                self.chat_display.insert(tk.END, f"[{username}]: ", "other_user")
                self.chat_display.insert(tk.END, f"{content}\n", "other_msg")
        
        # Configure text tags for styling
        self.chat_display.tag_configure("time", foreground="#2ecc71")
        self.chat_display.tag_configure("self_user", foreground="#3498db", font=("Arial", 11, "bold"))
        self.chat_display.tag_configure("self_msg", foreground="#2c3e50")
        self.chat_display.tag_configure("other_user", foreground="#e74c3c", font=("Arial", 11, "bold"))
        self.chat_display.tag_configure("other_msg", foreground="#333333")
        
        self.chat_display.config(state=tk.DISABLED)
        self.chat_display.see(tk.END)  # Scroll to bottom
    
    def send_message(self, event=None):
        message = self.message_entry.get().strip()
        if not message or not self.current_channel:
            return
        
        # Send the message
        channel_name = self.current_channel
        result = sendMessageTo(channel_name, message)
        
        if result == "Success":
            self.message_entry.delete(0, tk.END)
            # The message will appear in the next update
        else:
            messagebox.showerror("Error", f"Failed to send message: {result}")
    
    def update_messages(self):
        # Refresh messages if a channel is selected
        if self.current_channel:
            channel_name = self.current_channel
            self.load_channel_messages(channel_name)
        
        # Schedule the next update
        self.after(1000, self.update_messages)
    
    def manual_refresh(self):
        if self.current_channel:
            self.load_channel_messages(self.current_channel)

class App(tk.Tk):
    def __init__(self, client):
        super().__init__()
        self.title("Peer Messaging App")
        self.geometry("900x600")
        self.minsize(800, 500)
        
        self.client = client
        self.username = "User"
        
        # Create a container to hold all frames
        container = tk.Frame(self)
        container.pack(fill="both", expand=True)
        
        # Initialize frames dictionary
        self.frames = {}
        
        # Create all pages
        for F in (LoginPage, ChannelListPage, MessagingPage):
            frame = F(container, self)
            self.frames[F] = frame
            frame.grid(row=0, column=0, sticky="nsew")
        
        # Configure the container to expand with the window
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)
        
        # Show the login page first
        self.show_frame(LoginPage)
    
    def show_frame(self, page_class):
        """Raises the specified frame to the top"""
        frame = self.frames[page_class]
        frame.tkraise()

########################################
# Backend Logic Section
########################################

def peer_server(peer_host: PeerHost):
    peer_host.listen()

def getClient():
    return client

def exitFunc():
    for channel in getAllConnectedChannel():
        client.disconnect(channel['channel_name'])

def getAllChannel():
    return client.get_peer_hosts()

def getAllConnectedChannel():
    channel_list = []
    print("CH", client.channels)
    if client.channels:
        for key, host_key in client.channels.items():
            channel_list.append( {"channel_name": key, "peer-server-ip" : host_key['ip'], "peer_server_port" : host_key['port']} )
    return channel_list

def joinChannel(channel_name):
    hosts = client.get_peer_hosts()
    target_host = None
    for host in hosts:
        if host['channel_name'] == channel_name:
            target_host = host
            break
        
    if target_host:
        if channel_name in client.channels:
            return "Error: Already connected to channel"
        else:
            success = client.connect_to_host(target_host)
            if success:
                print(f"Joined channel: {channel_name}")
                return "Success"

    else:
        return "Error: Channel not found"
        
def getMessage(channel_name):
        # Display current messages for this channel
    with client.messages_lock:
        all_message = client.messages.get(channel_name, [])
        client._send_cached_messages(channel_name)
        return all_message

def sendMessageTo(channel_name, message):
    if channel_name in client.channels:
        client.send_message(message, channel_name)
        return "Success"
    else:
        client._cache_message(message, channel_name)
        return "Error: Not connected to this channel. Message will be cached for later delivery."
        
    
def disconectChannel(channel_name):
    if channel_name in client.channels:
        client.disconnect(channel_name)
        return "Success"
    else:
        return "Error: Not connected to this channel"   

if __name__ == "__main__": 
    parser = argparse.ArgumentParser(
                        prog='Peer',
                        description='Run as a peer in the network, can be both host and client',
                        epilog='!!!It requires the tracker to be running and listening!!!')
    parser.add_argument('--tracker-ip', default='localhost', help='IP address of the tracker')
    parser.add_argument('--tracker-port', type=int, default=5000, help='Port of the tracker')
    parser.add_argument('--peer-host-ip', default='localhost', help='IP address for hosting a peer server')
    parser.add_argument('--peer-host-port', type=int, default=0, help='Port for hosting a peer server, 0 for random')
    parser.add_argument('--channel-name', default='', help='Name of the channel to host, if empty, only client mode')
    parser.add_argument('--username', default='User', help='Username for the client')
    
    args = parser.parse_args()
    tracker_ip = args.tracker_ip
    tracker_port = args.tracker_port
    peer_host_ip = args.peer_host_ip
    peer_host_port = args.peer_host_port if args.peer_host_port != 0 else random.randint(6000, 7000)
    channel_name = args.channel_name
    username = args.username
    
    # Create PeerClient for client operations
    client = PeerClient(username, tracker_ip, tracker_port)
    
    # If channel name is provided, run as host as well
    if channel_name:
        peer_host = PeerHost(channel_name, username, peer_host_ip, peer_host_port, tracker_ip, tracker_port)
        Thread(target=peer_server, args=(peer_host,), daemon=True).start()
        print(f"Hosting channel '{channel_name}' on {peer_host_ip}:{peer_host_port}")
    
    # Start the GUI
    app = App(client)
    
    # When window is closed, disconnect from all peers
    app.protocol("WM_DELETE_WINDOW", lambda: [exitFunc(), app.destroy()])
    
    app.mainloop()