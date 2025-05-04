class Channel:
    def __init__(self, channel_name, host_ip, host_port):
        self.channel_name = channel_name
        self.host_ip = host_ip
        self.host_port = host_port
        self.list_of_messages = []
    
    def add_peer(self, peer):
        self.list_of_peers.append(peer)
    
    def remove_peer(self, peer):
        self.list_of_peers.remove(peer)
        
    def to_dict(self):
        return {
            "channel_name": self.channel_name,
            "host_ip": self.host_ip,
            "host_port": self.host_port,
            "list_of_messages": self.list_of_messages
        }
        
    @classmethod
    def from_dict(cls, data):
        channel = cls(data["channel_name"], data["host_ip"], data["host_port"])
        channel.list_of_messages = data.get("list_of_messages", [])
        return channel