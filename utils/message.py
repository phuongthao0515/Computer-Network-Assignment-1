from datetime import datetime

class Message:
    def __init__(self, username, message_content, time=None):
        if time is None:
            now = datetime.now()
            time = now.strftime("%H:%M:%S")
        self.username = username
        self.message_content = message_content
        self.time = time

    def to_dict(self):
        return {
            "username": self.username,
            "message_content": self.message_content,
            "time": str(self.time)
        }
        
    @classmethod
    def from_dict(cls, data):
        return cls(data["username"], data["message_content"], data["time"])

    def __repr__(self):
        return f"\033[94m[{self.time}]\033[0m\n\033[92m{self.username}:\033[0m {self.message_content}"

    def __str__(self):
        return f"\033[94m[{self.time}]\033[0m\n\033[92m{self.username}:\033[0m {self.message_content}"
 