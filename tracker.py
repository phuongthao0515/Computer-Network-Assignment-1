import socket
from threading import Thread
import json
from utils.protocol import create_response, parse_request, Status

def handle_user_submission(addr, conn):
    try:
        data = conn.recv(4096).decode("utf-8")
        if not data:
            print("No data received from", addr)
            return
        
        command, payload = parse_request(data)
        
        if command == "LIST":
            response = create_response(Status.OK, peers)
            conn.send(response.encode("utf-8"))
        elif command == "HOST":
            peers.append({
                "channel_name": payload['channel_name'],
                "peer_server_ip": payload['peer_server_ip'],
                "peer_server_port": payload['peer_server_port'],
            })
            response = create_response(Status.OK, {
                "status": "success",
                "channel_name": payload['channel_name'],
            }).encode("utf-8")
            conn.send(response)
        elif command == "MESSAGE":
            pass
        
    except ValueError as e:
        print("Error parsing data:", e)
        conn.close()
        return

def listen(ip, port):
    try:
        tracker_socket = socket.socket()
        tracker_socket.bind((ip, port))
        tracker_socket.listen(10)
        print(f"listening on {ip}:{port}...")
        
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