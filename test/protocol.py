import json
from enum import Enum

class Command(Enum):
    LIST = "LIST"
    HOST = "HOST"
    MESSAGE = "MESSAGE"
    BROADCAST = "BROADCAST"
    CACHE = "CACHE"
    SIGNIN = "SIGNIN"
    SIGNUP = "SIGNUP"
    GUEST = "GUEST"
    CONNECT = "CONNECT"
    VIEW = "VIEW"
    DEBUG = "DEBUG"
    
class Status(Enum):
    OK = "OK"
    REQUEST_ERROR = "REQUEST_ERROR"
    SERVER_ERROR = "SERVER_ERROR"
    UNAUTHORIZED = "UNAUTHORIZED"
    
def create_request(command, payload, separater = "\r\r"):
    """
    Create a request string to be sent to the tracker or peer.
    
    Args:
        command (Command): The command to be executed.
        payload (dict): The data associated with the command.
        separator (string): Separate symbol to split 2 different response 
    
    Returns:
        str: The formatted request string.
    """
    # Switch case for command
    if command == Command.LIST:
        request = f"{command.value}\r\n"
        
    elif command in [Command.HOST, Command.MESSAGE, Command.CACHE]:
        if isinstance(payload, dict):
            payload = [payload]
        request = f"{command.value}\r\n{json.dumps(payload)}"

    elif command in [Command.BROADCAST, Command.SIGNIN, Command.SIGNUP, Command.GUEST,
                     Command.CONNECT, Command.VIEW, Command.DEBUG]:
        request = f"{command.value}\r\n{json.dumps(payload)}"
        
    request = (request + separater).encode("utf-8")
    return request
    


def parse_request(response, isSeparated = False):
    """
    Parse the response string from the tracker or peer.
    
    Args:
        response (str): The response string to be parsed.
        isSeparated (bool): False: not using separater => response hasn't been decode
                            True: using separater => response has been decoded

    Returns:
        dict: The parsed response data.
    """
    try:
        if not isSeparated:
            response = response.decode("utf-8")
            response = response.split("\r\r", 1)[0]
        command, payload = response.split("\r\n", 1)
        if payload:
            payload = json.loads(payload)
        else:
            payload = {}
        return command, payload
    except ValueError:
        print(f"Error parsing response: {response}")
        raise ValueError("Invalid response format")
    
def create_response(status, payload, separater = "\r\r"):
    """
    Create a response string to be sent back to the client.
    
    Args:
        status (Status): The status of the response.
        payload (dict): The data associated with the response.
        separator (string): Separate symbol to split 2 different response 

    Returns:
        str: The formatted response string.
    """
    return f"{status.value}\r\n{json.dumps(payload)}{separater}".encode("utf-8")

def parse_response(response, isSeparated = False):
    """
    Parse the response string from the tracker or peer.
    
    Args:
        response (str): The response string to be parsed.
        isSeparated (bool): False: not using separater => response hasn't been decode
                            True: using separater => response has been decoded

    Returns:
        str: The status of the response.
        dict: The parsed response data.
    """
    try:
        if not isSeparated:
            response = response.decode("utf-8")
            response = response.split("\r\r", 1)[0]
        status, payload = response.split("\r\n", 1)
        if payload:
            payload = json.loads(payload)
        else:
            payload = {}
        return status, payload
    except ValueError:
        print(f"Error parsing response: {response}")
        raise ValueError("Invalid response format")