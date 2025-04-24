import socket
from threading import Thread
import json

def handle_user_submission(addr, conn):
    data = json.loads(conn.recv(1024).decode("utf-8"))

    if data['command_name'] == "LIST":
        conn.send(json.dumps(peers).encode("utf-8"))

    elif data['command_name'] == "HOST":
        peers.append({
            "channel_name": data['channel_name'],
            "peer_server_ip": data['peer_server_ip'],
            "peer_server_port": data['peer_server_port'],
        })
        conn.send("OK".encode("utf-8"))

    # elif data['command_name'] == "REGAIN CONTROL":
    #     list_channel = get_currently_hosting_channel(data)  # Ensure this function is implemented
    #     conn.send(json.dumps(list_channel).encode("utf-8"))

    # Optional: add the connection to keep track for broadcasting
    print("Finished handling user submission from", addr)

def listen(ip, port):
    try:
        tracker_socket = socket.socket()
        tracker_socket.bind((ip, port))
        tracker_socket.listen(10)
        print(f"Listening on {ip}:{port}...")
        
        while True:
            conn, addr = tracker_socket.accept()
            Thread(target=handle_user_submission, args=(addr, conn), daemon=True).start()

    except KeyboardInterrupt:
        print("Exiting...")
        
    finally:
        tracker_socket.close()

if __name__ == "__main__":
    
    # Dummy values for testing
    peers = []
    ip = '127.0.0.1'
    port = 22236
    listen(ip, port)