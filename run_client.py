import os
import time
import sys
import threading

from time import gmtime, strftime

import grpc
from proto import chat_pb2
from proto import chat_pb2_grpc

from client.chat_client import Client, run

# username as param
if __name__ == "__main__":
    args = sys.argv
    if (len(sys.argv) < 2):
        print('Run with parameter: username')
        exit(1)
    # Get ip
    ip = 'localhost'
    username = args[1]
    port = 50050
    client = Client(username, ip, port)
    channel = client.get_connection(client.default_thread)
    client.create_server_connection(channel, client.default_thread)
    client.connect()
    print('Connected to server with session {}\nWelcome to the chat {}'.format(list(client.sessions)[0], client.username))
    run(client)
