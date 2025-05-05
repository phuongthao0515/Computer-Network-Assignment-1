import argparse
import random
from peer.peer_host import PeerHost
from peer.peer_client import PeerClient
from threading import Thread
import tkinter as tk

class Page(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent)

class PageOne(Page):
    def __init__(self, parent, controller):
        super().__init__(parent)
        label = tk.Label(self, text="This is Page One")
        label.pack(pady=10)
        button = tk.Button(self, text="Go to Page Two", 
                           command=lambda: controller.show_frame(MainPage))
        button.pack()

class MainPage(Page):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        label = tk.Label(self, text="Available Channels", font=("Arial", 16))
        label.pack(pady=10)

        self.button_container = tk.Frame(self)
        self.button_container.pack(fill="both", expand=True)

        # populate buttons
        self.load_channels()

    def load_channels(self):
        # clear any existing buttons
        for child in self.button_container.winfo_children():
            child.destroy()

        channels = getAllChannel()
        if not channels:
            tk.Label(self.button_container, text="No channels found").pack()
            return

        for ch in channels:
            channel_name = ch.get("channel_name")
            btn = tk.Button(
                self.button_container, 
                text= channel_name, 
                width=20,
                command=lambda c=ch: self.on_channel_click(c)
            )
            btn.pack(pady=2)

    def on_channel_click(self, channel):
        # TODO: replace with your actual channel-open logic
        print(f"Channel clicked: {channel}")

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Multi-Page Example")
        self.geometry("300x200")
        
        container = tk.Frame(self)
        container.pack(fill="both", expand=True)

        self.frames = {}

        for F in (PageOne, MainPage):
            frame = F(container, self)
            self.frames[F] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        self.show_frame(MainPage)

    def show_frame(self, page_class):
        frame = self.frames[page_class]
        frame.tkraise()

def peer_server(peer_host: PeerHost):
    peer_host.listen()

def getClient():
    return client

def exitFunc():
    client.disconnect()

def getAllChannel():
    return client.get_peer_hosts()

def getAllConnectedChannel():
    dict = {}
    if client.hosts:
        for host_key in client.hosts:
            dict[host_key[0]] = host_key[1]
    return dict

def joinChannel():
    pass

def sendMessageTo( channel_name ,  message):
    hosts = client.get_peer_hosts()
    target_host = None
    for host in hosts:
        if host['channel_name'] == channel_name:
            target_host = host
            break
    if target_host:
        host_key = (target_host['peer_server_ip'], target_host['peer_server_port'])
        if host_key in client.hosts:
            client.send_message(message, host_key)
            return "Success"
        else:
            return "Error: Not connected to channel"
    else:
        return "Error: Channel not found"
    
def disconectChannel( channel_name):
    hosts = client.get_peer_hosts()
    target_host = None
    for host in hosts:
        if host['channel_name'] == channel_name:
            target_host = host
            break
    if target_host:
        host_key = (target_host['peer_server_ip'], target_host['peer_server_port'])
        if host_key in client.hosts:
            client.disconnect(host_key)
            return "Success"
        else:
            return "Error: Not connected to channel"
    else:
        return "Error: Channel not found"

# DONE
def client_interface(client: PeerClient):
    """Interactive interface for the client to interact with peer hosts."""
    print("Welcome to the Peer Chat Client!")
    print("Commands:")
    print("  /list - list all available channels")
    print("  /join <channel_name> - Join a specific channel")
    print("  /connected - list all connected channels")
    print("  /sendto <channel_name> <message> - Send a message to a specific channel")
    print("  /disconnect <channel_name> - Disconnect from a specific channel")
    print("  /exit - Exit the application")
    print("  Any other input will be sent as a message to all connected channels.")
    
    while True:
        try:
            user_input = input()
            
            if user_input.lower() == "/exit":
                exitFunc()
                break
            
            elif user_input.lower() == "/list":
                hosts = getAllChannel(client)
                print("Available Channels:")
                for host in hosts:
                    print(f"  - {host['channel_name']} at {host['peer_server_ip']}:{host['peer_server_port']}")
                    
            elif user_input.lower() == "/connected":
                if client.hosts:
                    print("Connected Channels:")
                    for host_key in client.hosts:
                        print(f"  - {host_key[0]}:{host_key[1]}")
                else:
                    print("Not connected to any channels.")
                    
            elif user_input.lower().startswith("/join "):
                channel_name = user_input.split(" ", 1)[1].strip()
                hosts = client.get_peer_hosts()
                target_host = None
                for host in hosts:
                    if host['channel_name'] == channel_name:
                        target_host = host
                        break
                    
                if target_host:
                    host_key = (target_host['peer_server_ip'], target_host['peer_server_port'])
                    if host_key in client.hosts:
                        print(f"Already connected to channel: {channel_name}")
                    else:
                        success = client.connect_to_host(target_host['peer_server_ip'], target_host['peer_server_port'])
                        if success:
                            print(f"Joined channel: {channel_name}")
                            # Display current messages for this host
                            with client.messages_lock:
                                print("Current Messages:")
                                for msg in client.messages.get(host_key, []):
                                    # Use ANSI escape codes for coloring
                                    RESET = "\033[0m"
                                    TIME_COLOR = "\033[92m"  # Green for time
                                    USER_COLOR = "\033[94m"  # Blue for username
                                    SELF_COLOR = "\033[97m"  # White for self messages
                                    
                                    if msg['username'] == client.username:
                                        print(f"{TIME_COLOR}{msg.get('time')}{RESET} {SELF_COLOR}[{msg['username']}]{RESET}: {msg['message_content']}")
                                    else:
                                        print(f"{TIME_COLOR}{msg.get('time')}{RESET} {USER_COLOR}[{msg['username']}]{RESET}: {msg['message_content']}")
                else:
                    print(f"Channel {channel_name} not found.")
                    
            elif user_input.lower().startswith("/sendto "):
                parts = user_input.split(" ", 2)
                if len(parts) < 3:
                    print("Usage: /sendto <channel_name> <message>")
                else:
                    channel_name = parts[1].strip()
                    message = parts[2].strip()
                    hosts = client.get_peer_hosts()
                    target_host = None
                    for host in hosts:
                        if host['channel_name'] == channel_name:
                            target_host = host
                            break
                    if target_host:
                        host_key = (target_host['peer_server_ip'], target_host['peer_server_port'])
                        if host_key in client.hosts:
                            client.send_message(message, host_key)
                        else:
                            print(f"Not connected to channel: {channel_name}. Use /join <channel_name> to connect.")
                    else:
                        print(f"Channel {channel_name} not found.")
                        
            elif user_input.lower().startswith("/disconnect "):
                channel_name = user_input.split(" ", 1)[1].strip()
                hosts = client.get_peer_hosts()
                target_host = None
                for host in hosts:
                    if host['channel_name'] == channel_name:
                        target_host = host
                        break
                if target_host:
                    host_key = (target_host['peer_server_ip'], target_host['peer_server_port'])
                    if host_key in client.hosts:
                        client.disconnect(host_key)
                    else:
                        print(f"Not connected to channel: {channel_name}")
                else:
                    print(f"Channel {channel_name} not found.")
                    
            else:
                print("You are not connected to any channel. Use /join <channel_name> to connect.")
        except KeyboardInterrupt:
            client.disconnect()
            break
        except Exception as e:
            print(f"Error in client interface: {e}")

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
    '''
python peer.py --tracker-ip 127.0.0.1 --tracker-port 22236 --peer-host-ip 127.0.0.1 --peer-host-port 20000 --channel-name first --username ken
python peer.py --tracker-ip 127.0.0.1 --tracker-port 22236 --peer-host-ip 127.0.0.1 --peer-host-port 20001 --channel-name second --username ben
    '''
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
        peer_host = PeerHost(channel_name, peer_host_ip, peer_host_port, tracker_ip, tracker_port)
        Thread(target=peer_server, args=(peer_host,), daemon=True).start()
        print(f"Hosting channel '{channel_name}' on {peer_host_ip}:{peer_host_port}")
    
    # Start client interface
    app = App()
    app.mainloop()
