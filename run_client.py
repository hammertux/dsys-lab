import os
import time
import sys
import threading

from time import gmtime, strftime

import grpc
from proto import chat_pb2
from proto import chat_pb2_grpc

from client.chat_client import Client, run

def try_connecting():
    client = Client(username, ip, port)
    res = client.connection.Connect(client.default_thread)
    return client, res

# port, username
if __name__ == "__main__":
    args = sys.argv
    if (len(sys.argv) < 2):
        print('Run with parameter: username')
        exit(1)
    # Get ip
    ip = 'localhost'
    username = args[1]
    port = 50051
    print('Connecting...')
    while True:
        try:
            client, res = try_connecting()
            break
        except:
            print('Connection failed')
            time.sleep(5)
            print('Retrying...')

    client.sessions[res.session.thread.uuid.hex] = {'session': res.session, 'messages_sent': 0, 'messages_received': 0, 'updates_received': 0}
    client.current_thread = res.session.thread.uuid.hex

    print('Connected to server with session {}Welcome to the chat {}'.format(res.session.uuid, client.username))
    run(client)
