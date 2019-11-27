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
    port = 50051
    client = Client(username, ip, port)
    client.connect()
    print('Connected to server with session {}\nWelcome to the chat {}'.format(list(client.sessions)[0], client.username))
    run(client)
