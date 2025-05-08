import socket
import copy
from threading import Thread, Lock
import json
from utils.protocol import create_response, parse, Status

# Tạm thời để separater là \n vì logic của peer vẫn chưa đc đổi
separater = '\n'

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

visitor_list = []
visitorLock = Lock()

channel_list = []
channelLock = Lock()


def get_list(conn, lock, request_id):    
    #TODO: REQUEST: GETLIST: send the channel list 
    global channel_list 
    try:
        with lock:
            safe_copy = copy.deepcopy(channel_list)
        response = create_response(request_id, Status.OK, safe_copy, separater)
        conn.send(response)

    except Exception as e:
        error_msg = create_response(request_id, Status.SERVER_ERROR, {"message": str(e)}, separater)

        try:
            conn.sendall(error_msg)
        except:
            pass 

        print(f"[Error] Failed to send: {e}")

def visitor(conn, lock, payload, request_id):
    global account_list
    try:
        with lock:
            if any(account['username'] == payload['username'] for account in account_list):
                message = {"Message": "Username is existed"}
                status = Status.REQUEST_ERROR
            else:    
                with visitorLock:
                    visitor_list.append(
                        {
                            "username": payload['username']
                        }
                    )
                message = {"message": f"Create visitor account {payload['username']} successful"}
                status = Status.OK
        
        response = create_response(request_id, status, message, separater) 
        conn.sendall(response)

    except Exception as e:
        error_msg = create_response(request_id, Status.SERVER_ERROR, {"message": str(e)}, separater)
        try:
            conn.sendall(error_msg)
        except:
            pass 

        print(f"[Error] Failed to send: {e}")

def authenticate_user(conn, lock, payload, request_id):
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
        
        response = create_response(request_id, status, message, separater) 
        conn.sendall(response)

    except Exception as e:
        error_msg = create_response(request_id, Status.SERVER_ERROR, {"message": str(e)}, separater)
        try:
            conn.sendall(error_msg)
        except:
            pass 

        print(f"[Error] Failed to send: {e}")   

def create_account(conn, lock, payload, request_id):
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

        response = create_response(request_id, status, message, separater) 
        conn.sendall(response)

    except Exception as e:
        error_msg = create_response(request_id, Status.SERVER_ERROR, {"message": str(e)}, separater)
        try:
            conn.sendall(error_msg)
        except:
            pass 

        print(f"[Error] Failed to send: {e}")  

def change_view_permission(conn, lock, payload, request_id):
    channel_name = payload.get("channel_name")
    view_permission = payload.get("view_permission")
    
    try:
        with lock:
            for channel in channel_list:
                if channel['channel_name'] == channel_name:
                    channel['view_permission'] = view_permission
                    message = {"message": f"Change view permission of {channel_name} successful"}
                    status = Status.OK
                    break
            else:
                message = {"message": f"Channel {channel_name} not found"}
                status = Status.REQUEST_ERROR
        
        response = create_response(request_id, status, message, separater) 
        conn.sendall(response)
    except Exception as e:
        error_msg = create_response(request_id, Status.SERVER_ERROR, {"message": str(e)}, separater)
        try:
            conn.sendall(error_msg)
        except:
            pass 

        print(f"[Error] Failed to send: {e}")
    

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
            
            #### Use seperater instead of \n
            while separater in buffer:
                # Split the buffer into individual requests
                request, buffer = buffer.split(separater, 1)
                
                if not request:
                    continue
                
                # Parse the request
                command, payload, request_id = parse(request,separator=separater, isSeparated=True)
                
                if command == "LIST":
                    Thread(target=get_list, args=(conn, channelLock, request_id), daemon=True).start()
                    
                # Only command from host to tracker (except SYNC)
                elif command == "HOST":
                    channel_list.append({
                        'channel_name': payload['channel_name'],
                        'peer_server_ip': payload['peer_server_ip'],
                        'peer_server_port': payload['peer_server_port'],
                        'view_permission': payload['view_permission'],
                    })
                    response = create_response(request_id, Status.OK, {}, separater)
                    conn.send(response)
                elif command == "VIEW":
                    Thread(target=change_view_permission, args=(conn, channelLock, payload, request_id), daemon=True).start()
                elif command == "SIGNIN":
                    Thread(target=authenticate_user, args=(conn, channelLock, payload, request_id), daemon=True).start()
                elif command == "SIGNUP":
                    Thread(target=create_account, args=(conn, channelLock, payload, request_id), daemon=True).start()
                elif command == "GUEST":
                    Thread(target=visitor, args=(conn, channelLock, payload, request_id), daemon=True).start()
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
    # peers = [] => Thống nhất dùng channel list
    ip = '127.0.0.1'
    port = 22236
    listen(ip, port)