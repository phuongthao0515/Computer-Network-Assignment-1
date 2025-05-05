# Protocol Structure

## Request Structure
The protocol structure includes 2 parts: Command and Payload.

### Command Format
`<command>`

Where `<command>` is a string that indicates the type of command being sent including:
- `LIST`: List all available channels
- `HOST`: Host a new channel
- `MESSAGE`: Send a message to the channel

### Payload Format
- For `LIST`: No payload is needed.
- For `HOST`: JSON object containing `channel_name`, `peer_server_ip`, and `peer_server_port`.
- For `MESSAGE`: JSON object containing `username` and `message_content`.

Command and payload are separated by the character sequence `\r\n`.

### Examples

1. List available channels:
```
LIST\r\n
```

2. Host a new channel:
```
HOST\r\n{"channel_name": "test_channel", "peer_server_ip": "127.0.0.1", "peer_server_port": 22236}
```

3. Send a message:
```
MESSAGE\r\n{"username": "user1", "message_content": "Hello, World!"}
```

## Response Structure

All responses follow a consistent format consisting of a status code and a payload.

### Response Format
```
<status_code>\r\n<response_payload>
```

### Status Codes
- `OK`: The command was processed successfully
- `REQUEST_ERROR`: The client request was invalid (e.g., malformed payload, missing required fields)
- `SERVER_ERROR`: An error occurred on the server while processing the request

### Response Payload Format
Response payloads are formatted as JSON objects with contents specific to each command:

#### LIST Command Response
Returns an array of available channels with their connection details:
```
OK\r\n{"channels": [{"channel_name": "test_channel", "peer_server_ip": "127.0.0.1", "peer_server_port": 22236}, {"channel_name": "general", "peer_server_ip": "192.168.1.5", "peer_server_port": 22240}]}
```

#### HOST Command Response
Returns confirmation of channel creation:
```
OK\r\n{"status": "success", "channel_name": "test_channel"}
```

#### MESSAGE Command Response
Returns confirmation of message delivery:
```
OK\r\n{"status": "delivered", "timestamp": "2023-11-02T15:04:32Z"}
```

### Error Response Examples
For invalid client requests:
```
REQUEST_ERROR\r\n{"error": "Invalid payload", "details": "Missing required field 'channel_name'"}
```

```
REQUEST_ERROR\r\n{"error": "Channel not found", "details": "The requested channel 'gaming' does not exist"}
```

For server-side errors:
```
SERVER_ERROR\r\n{"error": "Database connection failed", "details": "Unable to store message in channel database"}
```