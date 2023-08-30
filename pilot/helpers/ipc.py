# ipc.py
import socket
import json
import time

class IPCClient:
    def __init__(self):
        self.ready = False
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        print("Connecting to the external process...")
        try:
            client.connect(('localhost', 8124))
            self.client = client
            print("Connected!")
        except ConnectionRefusedError:
            self.client = None
            print("Connection refused, make sure you started the external process")

    def handle_request(self, message_content):
        print(f"Received request from the external process: {message_content}")
        return message_content  # For demonstration, we're just echoing back the content

    def listen(self, cb):
        if self.client is None:
            print("Not connected to the external process!")
            return
        try:
            while True:
                data = self.client.recv(4096)
                message = json.loads(data)

                if message['type'] == 'request':
                    cb(message['content'])
                if message['type'] == 'request':
                    response_content = self.handle_request(message['content'])
                    response = {
                        'type': 'response',
                        'content': response_content
                    }
                    self.client.sendall(json.dumps(response).encode('utf-8'))
                    time.sleep(0.1)

                    serialized_data = json.dumps(data)
                    self.client.sendall(serialized_data.encode('utf-8'))

        finally:
            self.client.close()

    def send(self, data):
        serialized_data = json.dumps(data)
        self.client.sendall(serialized_data.encode('utf-8'))
        time.sleep(0.1)
