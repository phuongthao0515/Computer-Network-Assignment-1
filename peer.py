import argparse
import random
from peer.peer_host import PeerHost
from peer.peer_client import PeerClient
from threading import Thread

def peer_server(peer_host: PeerHost):
    peer_host.listen()

def client_interface(client: PeerClient):
    """Interactive interface for the client to interact with peer hosts."""
    print("Welcome to the Peer Chat Client!")
    print("Commands:")
    print("  /list - List all available channels")
    print("  /join <channel_name> - Join a specific channel")
    print("  /exit - Exit the application")
    print("  Any other input will be sent as a message to the current channel.")
    
    while True:
        try:
            user_input = input()
            if user_input.lower() == "/exit":
                client.disconnect()
                break
            elif user_input.lower() == "/list":
                hosts = client.get_peer_hosts()
                print("Available Channels:")
                for host in hosts:
                    print(f"  - {host['channel_name']} at {host['peer_server_ip']}:{host['peer_server_port']}")
            elif user_input.lower().startswith("/join "):
                channel_name = user_input.split(" ", 1)[1].strip()
                hosts = client.get_peer_hosts()
                target_host = None
                for host in hosts:
                    if host['channel_name'] == channel_name:
                        target_host = host
                        break
                if target_host:
                    # Disconnect from current host if connected
                    if client.current_host:
                        client.disconnect()
                    success = client.connect_to_host(target_host['peer_server_ip'], target_host['peer_server_port'])
                    if success:
                        print(f"Joined channel: {channel_name}")
                        # Display current messages
                        with client.messages_lock:
                            print("Current Messages:")
                            for msg in client.messages:
                                # Use ANSI escape codes for coloring
                                RESET = "\033[0m"
                                TIME_COLOR = "\033[92m"  # Green for time
                                USER_COLOR = "\033[94m"  # Blue for username
                                SELF_COLOR = "\033[97m"  # White for self messages
                                
                                if msg.username == client.username:
                                    print(f"{TIME_COLOR}{msg.time}{RESET} {USER_COLOR}[{msg.username}]{RESET}: {SELF_COLOR}{msg.message_content}{RESET}")
                                else:
                                    print(f"{TIME_COLOR}{msg.time}{RESET} {USER_COLOR}[{msg.username}]{RESET}: {msg.message_content}")
                else:
                    print(f"Channel {channel_name} not found.")
            elif client.current_host:
                # Send as a message to the current host
                client.send_message(user_input)
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
    client_interface(client)