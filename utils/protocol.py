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
    
class Status(Enum):
    OK = "OK"
    REQUEST_ERROR = "REQUEST_ERROR"
    SERVER_ERROR = "SERVER_ERROR"
    UNAUTHORIZED = "UNAUTHORIZED"
    
def create_request(command, payload, separator="\\"):
    """
    Create a request string to be sent to the tracker or peer.
    
    Args:
        command (Command): The command to be executed.
        payload (dict): The data associated with the command.
        
    Returns:
        str: The formatted request string.
    """
    # Switch case for command
    if command == Command.LIST:
        return f"{command.value}\r\n{separator}".encode("utf-8")
    elif command == Command.HOST:
        # If the payload is a dictionary, convert it to a list of dictionaries
        if isinstance(payload, dict):
            payload = [payload]
        return f"{command.value}\r\n{json.dumps(payload) + separator}".encode("utf-8")
    elif command == Command.MESSAGE:
        # If the payload is a dictionary, convert it to a list of dictionaries
        if isinstance(payload, dict):
            payload = [payload]
        return f"{command.value}\r\n{json.dumps(payload) + separator}".encode("utf-8")
    elif command == Command.CACHE:
        # If the payload is a dictionary, convert it to a list of dictionaries
        if isinstance(payload, dict):
            payload = [payload]
        return f"{command.value}\r\n{json.dumps(payload) + separator}".encode("utf-8")
    elif command == Command.BROADCAST:
        return f"{command.value}\r\n{json.dumps(payload) + separator}".encode("utf-8")
    elif command == Command.SIGNIN:
        return f"{command.value}\r\n{json.dumps(payload) + separator}".encode("utf-8")
    elif command == Command.SIGNUP:
        return f"{command.value}\r\n{json.dumps(payload) + separator}".encode("utf-8")
    elif command == Command.GUEST:
        return f"{command.value}\r\n{json.dumps(payload) + separator}".encode("utf-8")
    

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
        command, payload = response.split("\r\n", 1)
        if payload:
            payload = json.loads(payload)
        else:
            payload = {}
        return command, payload
    except ValueError:
        print(f"Error parsing response: {response}")
        raise ValueError("Invalid response format")
    
def create_response(status, payload, separator = "\\"):
    """
    Create a response string to be sent back to the client.
    
    Args:
        status (Status): The status of the response.
        payload (dict): The data associated with the response.
        separator (string): Separate symbol to split 2 different response 
    Returns:
        str: The formatted response string.
    """
    return f"{status.value}\r\n{json.dumps(payload) + separator}".encode("utf-8")

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
            response = response.split("\\", 1)[0]

        status, payload = response.split("\r\n", 1)
        if payload:
            payload = json.loads(payload)
        else:
            payload = {}
        return status, payload
    except ValueError:
        print(f"Error parsing response: {response}")
        raise ValueError("Invalid response format")