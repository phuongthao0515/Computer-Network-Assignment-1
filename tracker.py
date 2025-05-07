import socket
from threading import Thread
import json
from utils.protocol import create_response, parse, Status

def handle_user_submission(addr, conn):
    # Buffer to handle multiple requests at once
    buffer = ""
    
    try:
        while True:
            data = conn.recv(4096)
            if not data:
                print(f"Connection closed by {addr}")
                return
            
            buffer += data.decode("utf-8")
            
            while '\n' in buffer:
                # Split the buffer into individual requests
                request, buffer = buffer.split('\n', 1)
                
                if not request:
                    continue
                
                # Parse the request
                command, payload, request_id = parse(request, isSeparated=True)
                
                if command == "LIST":
                    response = create_response(request_id, Status.OK, peers)
                    conn.send(response)
                    
                # Only command from host to tracker (except SYNC)
                elif command == "HOST":
                    peers.append({
                        'channel_name': payload['channel_name'],
                        'peer_server_ip': payload['peer_server_ip'],
                        'peer_server_port': payload['peer_server_port'],
                    })
                    response = create_response(request_id, Status.OK, {})
                    conn.send(response)
                
                else:
                    print(f"Command not serve {command}")
            
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