# import grpc
# from proto import chat_pb2
# from proto import chat_pb2_grpc
# def run():
#   with grpc.insecure_channel('localhost:50051') as channel:
#     chat_server = chat_pb2_grpc.ChatServerStub(channel)
#     default_thread = chat_pb2.Thread()
#     connectionResponse = chat_server.Connect(default_thread)
#     print(connectionResponse.session.uuid)
#     print("Connection successful")

# if __name__ == '__main__':
#   run()

import os
import time
import sys
import threading

from time import gmtime, strftime

import grpc
from proto import chat_pb2
from proto import chat_pb2_grpc

class Client:
    def __init__(self, username, ip, port):
        self.username = username
        self.channel = grpc.insecure_channel(ip + ':' + str(port))
        self.connection = chat_pb2_grpc.ChatServerStub(self.channel)
        self.default_thread = chat_pb2.Thread()
        self.current_thread = None

        # Key: thread
        # Value: dict(session, messages_sent, messages_received updates_received)
        self.sessions = {}

    def start_listening(self):
        threading.Thread(target=self._listen, daemon=True).start()

    def _listen(self):
        # For every session
        for thread, s in self.sessions.items():
            session = s['session']
            # Get server updates
            for update in self.connection.ReceiveUpdates(session):
                # Handle update
                self.handle_update(update)
                # Acknowledge
                acknowledgement = chat_pb2.Acknowledgement(
                    session = session,
                    numUpdatesReceived = s['updates_received'],
                    numMessagesReceived = s['messages_received'],
                    numMessagesSent = s['messages_sent']
                )
                timestamp = self.connection.Acknowlegde(acknowledgement)

    def handle_update(self, update):
        message = update.message
        self.display(message)

    def display(self, msg):
        print(msg.serverTime + ' | ' + msg.thread + ' | ' + msg.sender + ': ' + msg.contents + "\n")

    def handle_input(self, user_input):
        time = strftime("%Y-%m-%d %H:%M:%S", gmtime())
        # print(time + ' | ' + self.username + ': ' + user_input + "\n")
        
        # Get thread
        in_split = user_input.split(' ')
        if len(in_split) > 1 and user_input.split(' ')[-2] == '|':
            self.current_thread = user_input.split(' ')[-1]

        # Send message to server
        s = self.sessions[self.current_thread] 
        acknowledgement = chat_pb2.Acknowledgement(
            session = s['session'],
            numUpdatesReceived = s['updates_received'],
            numMessagesReceived = s['messages_received'],
            numMessagesSent = s['messages_sent']
        )
        msg_obj = chat_pb2.SentMessage(
            acknowledgement=acknowledgement,
            contents=user_input,
            timestamp=chat_pb2.ServerTime(timestamp=self.current_time())
        )
        status = self.connection.SendMessage(msg_obj)
        print('Sent message status: ' + str(status.statusCode))

    def current_time(self):
        return int(round(time.time() * 1000 * 1000))

def run(client):
    client.start_listening()
    while True:
        message = input("")
        client.handle_input(message)
    client.connection_config.connection.close()

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
