import socket
import time
import argparse
import json

from threading import Thread

def new_connection(tid, host, port):
    def submit_info(data):
        sendData = data.encode("utf-8")
        peer_socket.send(sendData)


    peer_socket = socket.socket()
    peer_socket.connect((host, port))
    #receive welcome
    welcome = peer_socket.recv(1024).decode()
    print(f"[Thread-{tid}] Server says: {welcome.strip()}")
    
    ########### INPUT INTERFACE ############
    while True:
        choice = input(f"[Thread-{tid}] [1] Sign up or [2] Sign in? (Enter 1 or 2): ").strip()
        if choice == '1':
            action = "SIGNUP"
            break
        elif choice == '2':
            action = "AUTHENTICATE"
            break
        else:
            print(f"[Thread-{tid}] Invalid choice. Please enter 1 or 2.")

    username = input(f"[Thread-{tid}] Enter username: ")
    password = input(f"[Thread-{tid}] Enter password: ")
    

    ########## REQUEST #########     
    
    request = {
    "action": action,
    "username": username,
    "password": password
    }
    peer_socket.sendall((json.dumps(request) + '\n').encode())
    response = peer_socket.recv(4096)
    print(f"[Thread-{tid}] Login response: {response.decode()}")
    
    # if login successfully, request GETLIST
    try:
        response_json = json.loads(response)
        
        if response_json.get("type") == "Success":
            print(f"[Thread-{tid}] {response_json.get('data')}")
            
            getlist_request = {
                "action": "GETLIST"
            }
            peer_socket.sendall((json.dumps(getlist_request)+'\n').encode())
            getlist_response = peer_socket.recv(4096).decode()

            try:
                response = json.loads(getlist_response)
                print(f"[Thread-{tid}] Received channel list:")

                if response["type"] == "list":
                    for ch in response["data"]:
                        print(ch)
                elif response["type"] == "error":
                    print("Server error:", response["message"])
                else:
                    print("Unexpected message:", response)
            except json.JSONDecodeError:
                print(f"[Thread-{tid}] Failed to decode GETLIST response: {getlist_response}")

        else:
            print(f"[Thread-{tid}] Authentication failed.")
    except json.JSONDecodeError:
        print(f"[Thread-{tid}] Failed to decode {request.get('action')} response: {response}")

    peer_socket.close()



def connect_server(threadnum, host, port):

    # Create "threadnum" of Thread to parallelly connnect
    threads = [Thread(target=new_connection, args=(i, host, port)) for i in range(0,threadnum)]
    [t.start() for t in threads]

    # TODO: wait for all threads to finish
    [t.join() for t in threads]

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
                        prog='Client',
                        description='Connect to pre-declard server',
                        epilog='!!!It requires the server is running and listening!!!')
    parser.add_argument('--server-ip')
    parser.add_argument('--server-port', type=int)
    parser.add_argument('--client-num', type=int)
    args = parser.parse_args()
    host = args.server_ip
    port = args.server_port
    cnum = args.client_num
    connect_server(cnum, host, port)
