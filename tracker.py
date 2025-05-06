import socket
import copy
from threading import Thread, Lock
import json
from utils.protocol import create_response, parse_request, Status

separater = '\t'
lock = Lock()
account_list = [
    {
        "username":"phuongthao",
        "password":"15052004",
    },
    {
        "username":"thuytien",
        "password":"04032004",
    },
    {
        "username":"minhhieu",
        "password":"07042004",
    },
    {
        "username":"diennguyen",
        "password":"12345678",
    },
    {
        "username":"thanhtam",
        "password":"987654",
    },
    {
        "username":"tienphat",
        "password":"0246810",
    }
]

visitor_list = [

]

channel_list = [
    {
        "channel_name": "MusicZone",
        "ip": "192.168.1.10",
        "port": 2222
    },
    {
        "channel_name": "GameChat",
        "ip": "192.168.1.11",
        "port": 2223
    }
]


def get_list(conn, lock):    
    #TODO: REQUEST: GETLIST: send the channel list 
    global channel_list 
    try:
        with lock:
            safe_copy = copy.deepcopy(channel_list)
        response = create_response(Status.OK, safe_copy, separater)
        conn.sendall(response)

    except Exception as e:
        error_msg = create_response(Status.SERVER_ERROR, {"message": str(e)})

        try:
            conn.sendall(error_msg)
        except:
            pass 

        print(f"[Error] Failed to send: {e}")

def visitor(conn, lock, payload):
    global account_list
    try:
        with lock:
            if any(account['username'] == payload['username'] for account in account_list):
                message = {"Message": "Username is existed"}
                status = Status.REQUEST_ERROR
            else:    
                visitor_list.append(
                    {
                        "username": payload['username']
                    }
                )
                message = {"message": f"Create visitor account {payload['username']} successful"}
                status = Status.OK
        
        response = create_response(status, message, separater) 
        conn.sendall(response)

    except Exception as e:
        error_msg = create_response(Status.SERVER_ERROR, {"message": str(e)})
        try:
            conn.sendall(error_msg)
        except:
            pass 

        print(f"[Error] Failed to send: {e}")
    

def authenticate_user(conn, lock, payload):
    global account_list
    message = {"message": "Invalid username or password"}
    status = Status.REQUEST_ERROR

    try:
        with lock:
            for account in account_list:
                if account['username'] == payload['username'] and account['password'] == payload['password']:
                    message = {"message": "Login successful"}
                    status = Status.OK
                    break
        
        response = create_response(status, message, separater) 
        conn.sendall(response)

    except Exception as e:
        error_msg = create_response(Status.SERVER_ERROR, {"message": str(e)})
        try:
            conn.sendall(error_msg)
        except:
            pass 

        print(f"[Error] Failed to send: {e}")    
    
    

def create_account(conn, lock, payload):
    #TODO: REQUEST: CREATEACC: check duplicate username, then add to the account_list
    global account_list
    username = payload.get("username")
    password = payload.get("password")

    try:
        with lock:
            if any(acc["username"] == username for acc in account_list):
                message = {"message": "Username already been used"}
                status = Status.REQUEST_ERROR 
            else:    
                account_list.append(
                    {
                        "username": username,
                        "password": password
                    }
                )
                message = {"message": f"Create user account {username} successful"}
                status = Status.OK

        response = create_response(status, message, separater) 
        conn.sendall(response)

    except Exception as e:
        error_msg = create_response(Status.SERVER_ERROR, {"message": str(e)})
        try:
            conn.sendall(error_msg)
        except:
            pass 

        print(f"[Error] Failed to send: {e}")  





def handle_user_submission(addr, conn):
    global lock   

    
    ## Handle user request (while loop for listening)##
    buffer = ""

    while True:
        try:
            data = conn.recv(4096)
            if not data:
                print("No data received from", addr)
                return
            buffer += data.decode("utf-8")

            while separater in buffer:
                line, buffer = buffer.split(separater,1)
                command, payload = parse_request(line, isSeparated=True)
                
                if command == "LIST":
                    Thread(target=get_list, arg=(conn, lock), daemon=True).start()
                    
                elif command == "HOST":
                    # peers.append({
                    #     "channel_name": payload['channel_name'],
                    #     "peer_server_ip": payload['peer_server_ip'],
                    #     "peer_server_port": payload['peer_server_port'],
                    # })
                    # response = create_response(Status.OK, {
                    #     "status": "success",
                    #     "channel_name": payload['channel_name'],
                    # })
                    # conn.sendall(response)
                    pass
                elif command == "SIGNIN":
                    Thread(target=authenticate_user, args=(conn, lock, payload), daemon=True).start()
                elif command == "SIGNUP":
                    Thread(target=create_account, args=(conn, lock, payload), daemon=True).start()
                elif command == "GUEST":
                    Thread(target=visitor, args=(conn, lock, payload), daemon=True).start()
                else:
                    pass
            
        except ValueError as e:
            print("Error parsing data:", e)
            return
        
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
    ip = '127.0.0.1'
    port = 22236
    listen(ip, port)