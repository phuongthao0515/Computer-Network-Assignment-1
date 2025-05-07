import json
from enum import Enum
from uuid import uuid4

class Command(Enum):
    LIST = "LIST"
    HOST = "HOST"
    MESSAGE = "MESSAGE"
    SIGNIN = "SIGNIN"
    SIGNUP = "SIGNUP"
    GUEST = "GUEST"
    CONNECT = "CONNECT"
    VIEW = "VIEW"
    DEBUG = "DEBUG"
    AUTHORIZE = "AUTHORIZE"
    BROADCAST = "BROADCAST"
    CACHE = "CACHE"
    
class Status(Enum):
    OK = "OK"
    REQUEST_ERROR = "REQUEST_ERROR"
    SERVER_ERROR = "SERVER_ERROR"
    UNAUTHORIZED = "UNAUTHORIZED"
    
def create_request(command, payload = {}, request_id = None, separator="\n"):
    """
    Create a request string to be sent to the tracker or peer.
    
    Args:
        command (Command): The command to be executed.
        payload (dict or list): The data associated with the command.
        request_id (str, optional): A unique identifier for the request. If None, a UUID will be generated.
        separator (str, optional): The string used to terminate the request. Defaults to newline character.
        
    Returns:
        str: The formatted request string in the format "command-{json data}{separator}".
    """
    request_body = {}
    
    # 1. Add request_id
    if request_id is None:
        request_id = str(uuid4())
    request_body['id'] = request_id
    
    # 2. Convert to list
    # MAYBE NEED FIX
    # [Command.HOST, Command.MESSAGE,
    #                  Command.CACHE, Command.BROADCAST,
    #                  Command.SIGNIN, Command.SIGNUP, Command.GUEST]:
    if command in [Command.MESSAGE]:
        # If the payload is a dictionary, convert it to a list of dictionaries
        if isinstance(payload, dict):
            payload = [payload]
    
    # 3. Add payload
    request_body['payload'] = payload
    return f"{command.value}-{json.dumps(request_body)}{separator}".encode('utf-8')

def create_response(response_id, status, payload = {}, separator = "\n"):
    """
    Create a response string to be sent back to the client.
    
    Args:
        status (Status): The status of the response.
        payload (dict): The data associated with the response.
        response_id (str): The ID extracted from the request
        separator (string): Separate symbol to split 2 different response 
    Returns:
        str: The formatted response string.
    """
       
    response_body = {}
    response_body['id'] = response_id
    response_body['payload'] = payload
    return f"{status.value}-{json.dumps(response_body)}{separator}".encode('utf-8')

def parse(message, isSeparated=False, separator="\n"):
    try:
        if not isSeparated:
            # Decode and remove separator charactor
            message = message.decode("utf-8")
            message = message.split(separator, 1)[0]

        header, body = message.split("-", 1)
        body = json.loads(body)
        payload = body['payload']
        id = body['id']
        return header, payload, id
    
    except Exception as e:
        print(f"Error parsing request: {message}")
        raise ValueError("Invalid request format") from e