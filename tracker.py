import socket
from threading import Thread
import json
from utils.protocol import create_response, parse_request, Status

def handle_user_submission(addr, conn):
    # Buffer to handle multiple requests at once
    buffer = ""
    
    try:
        while True:
            data = conn.recv(4096)
            print("data:", data)
            if not data:
                print("No data received from", addr)
                return
            
            buffer += data.decode("utf-8")
            
            while '\\' in buffer:
                # Split the buffer into individual requests
                request, buffer = buffer.split('\\', 1)
                
                if not request:
                    continue
                
                # Parse the request
                command, payload = parse_request(request, isSeparated=True)
                
                if command == "LIST":
                    response = create_response(Status.OK, peers)
                    conn.send(response)
                elif command == "HOST":
                    # A host can have multiple channels
                    for peer in payload:
                        peers.append(peer)
                        
                    response = create_response(Status.OK, {
                        "status": "success",
                        "channel_name": [peer["channel_name"] for peer in payload],
                    })
                    conn.send(response)
                elif command == "MESSAGE":
                    pass
            
    except ValueError as e:
        print("Error parsing data:", e)
        return
    finally:
        conn.close()

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