# ipc.py
import socket
import json
import time

from utils.utils import json_serial

class IPCClient:
    def __init__(self, port):
        self.ready = False
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        print("Connecting to the external process...")
        try:
            client.connect(('localhost', int(port)))
            self.client = client
            print("Connected!")
        except ConnectionRefusedError:
            self.client = None
            print("Connection refused, make sure you started the external process")

    def handle_request(self, message_content):
        print(f"Received request from the external process: {message_content}")
        return message_content  # For demonstration, we're just echoing back the content

    def listen(self):
        if self.client is None:
            print("Not connected to the external process!")
            return

        while True:
            data = self.client.recv(65536)
            message = json.loads(data)

            if message['type'] == 'response':
                # self.client.close()
                return message['content']

    def send(self, data):
        serialized_data = json.dumps(data, default=json_serial)
        data_length = len(serialized_data)
        if self.client is not None:
            self.client.sendall(data_length.to_bytes(4, byteorder='big'))
            self.client.sendall(serialized_data.encode('utf-8'))
