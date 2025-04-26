import socket
import json
from threading import Thread, Lock
#from database import *

#FORMAT FOR SENDING DATA USING JSON:
#{
# "type":
# "data": 
#}
#type: error, banner, .....

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

channel_list = [
    {
        "channel_id": "0001",
        "channel_name": "MusicZone",
        "ip": "192.168.1.10",
        "port": 2222
    },
    {
        "channel_id": "0002",
        "channel_name": "GameChat",
        "ip": "192.168.1.11",
        "port": 2223
    }
]


def get_list(conn, lock):    
    #TODO: REQUEST: GETLIST: send the channel list 
    
    try:
        global channel_list
        data = {
            "type": "list",
            "data": channel_list
        }
        converted = json.dumps(data)
        conn.sendall((converted + '\n').encode("utf-8")) 
    
    except Exception as e:
        error_msg = {"type": "error", "message": str(e)}

        try:
            with lock:
                conn.sendall((json.dumps(error_msg) + '\n').encode('utf-8'))
        except:
            pass 

        print(f"[Error] Failed to get list: {e}")

def authenticate_user(conn, lock, request):
    try:
        username = request.get("username")
        password = request.get("password")
        message = {
            "type": "Failed",
            "data": "Invalid username or password"
        }
        for account in account_list:
            if account["username"] == username and account["password"] == password:
                message = {
                    "type": "Success",
                    "data": "Login successful"
                }
                break

    except Exception as e:
        message = {"type": "Error", "data": str(e)}
    with lock: 
        conn.sendall((json.dumps(message)+'\n').encode("utf-8"))
    

def create_account(conn, lock, request):
    #TODO: REQUEST: CREATEACC: check duplicate username, then add to the account_list
    try:
        username = request.get("username")
        password = request.get("password")
        if not username or not password:
            raise ValueError("Null username/password")
        
        if any(acc["username"] == username for acc in account_list):
            message = {
                    "type": "Failed",
                    "data": "Username already been used"
                } 
        else:    
            account_list.append(
                {
                    "username": username,
                    "password": password
                }
            )
            message = {
                "type": "Success",
                "data": f"Create account {username} successful"
            }
    except Exception as e:
        message = {"type": "Error", "data": str(e)}

    with lock:
        conn.sendall((json.dumps(message) + '\n').encode("utf-8"))
            

#addr of the peer
def new_connection(addr, conn):
    lock = Lock()

    #TODO: REQUEST: CREATE channel 

    #TODO: REQUEST: AUTHENTICATE 
            
    print(f"connected: {addr}\n")
    #send welcome
    banner = {"type": "banner", "data": "Welcome to server"}
    conn.sendall(json.dumps(banner).encode('utf-8'))

    ## Handle user request (while loop for listening)##
    buffer = ""

    while True:
        try:
            #receive request jsonjson   
            receive = conn.recv(4096)
            if not receive:
                break
            buffer += receive.decode("utf-8")
            
            ## handle if there are multiple request receive at the same time:
            while '\n' in buffer:
                line, buffer = buffer.split('\n',1)
                try:
                    request = json.loads(line)
    
                    print(f"Received:{request}")
                    action = request.get('action')
                    
                    #handle request
                    if action == 'GETLIST':
                        Thread(target=get_list, args=(conn, lock), daemon=True).start()
                    elif action == 'SIGNUP':
                        Thread(target=create_account, args=(conn, lock, request), daemon=True).start()
                    elif action == 'AUTHENTICATE':
                        Thread(target=authenticate_user, args=(conn, lock, request), daemon=True).start()
                    else:
                        print(f"[WARN] Unknown action: {request!r}")
                    
                except json.JSONDecodeError:
                    print(f"[ERROR] Bad JSON: {line!r}")
                    break
                    
        except Exception as e:
            print("error")

    #conn.close()


    
def get_host_default_interface_ip():
    # create a socket UDP (But not a real connection for sending data)
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
       #pretend connect to Google DNS so that the OS will choose an appropriate interface
       s.connect(('8.8.8.8',1))
       #return IP that the computer use to "connect", so we can get the default IP
       ip = s.getsockname()[0]
    except Exception:
       ip = '192.168.56.101'
    finally:
       s.close()
    return ip


def server_program(host, port):
    #create TCP socket with default AF_INET and SOCK_DGRAM
    serversocket = socket.socket()
    #set the fixed ip and port
    serversocket.bind((host, port))

    serversocket.listen(10)
    while True:
        conn, addr = serversocket.accept()
        
        nconn = Thread(target=new_connection, args=(addr, conn))
        nconn.start()


if __name__ == "__main__":
    #hostname = socket.gethostname()
    hostip = get_host_default_interface_ip()
    port = 22236
    print("Listening on: {}:{}".format(hostip,port))
    server_program(hostip, port)
