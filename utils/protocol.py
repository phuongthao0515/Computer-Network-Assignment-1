import json
from enum import Enum

class Command(Enum):
    LIST = "LIST"
    HOST = "HOST"
    MESSAGE = "MESSAGE"
    BROADCAST = "BROADCAST"
    
class Status(Enum):
    OK = "OK"
    REQUEST_ERROR = "REQUEST_ERROR"
    SERVER_ERROR = "SERVER_ERROR"
    
def create_request(command, payload):
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
        return f"{command.value}\r\n".encode("utf-8")
    elif command == Command.HOST:
        return f"{command.value}\r\n{json.dumps(payload)}".encode("utf-8")
    elif command == Command.MESSAGE:
        return f"{command.value}\r\n{json.dumps(payload)}".encode("utf-8")
    elif command == Command.BROADCAST:
        return f"{command.value}\r\n{json.dumps(payload)}".encode("utf-8")
    

def parse_request(response):
    """
    Parse the response string from the tracker or peer.
    
    Args:
        response (str): The response string to be parsed.
        
    Returns:
        dict: The parsed response data.
    """
    try:
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
    
def create_response(status, payload):
    """
    Create a response string to be sent back to the client.
    
    Args:
        status (Status): The status of the response.
        payload (dict): The data associated with the response.
        
    Returns:
        str: The formatted response string.
    """
    return f"{status.value}\r\n{json.dumps(payload)}".encode("utf-8")

def parse_response(response):
    """
    Parse the response string from the tracker or peer.
    
    Args:
        response (str): The response string to be parsed.
    
    Returns:
        str: The status of the response.
        dict: The parsed response data.
    """
    try:
        response = response.decode("utf-8")
        status, payload = response.split("\r\n", 1)
        if payload:
            payload = json.loads(payload)
        else:
            payload = {}
        return status, payload
    except ValueError:
        print(f"Error parsing response: {response}")
        raise ValueError("Invalid response format")