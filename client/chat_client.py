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

        # Key: session uuid hex
        # Value: dict(session, messages_sent, messages_received updates_received)
        self.sessions = {}

    def connect(self, thread=None):
        while True:
            try:
                if thread == None:
                    thread = self.default_thread
                res = self.connection.Connect(thread)
                break
            except:
                print('Connection failed')
                time.sleep(5)
                print('Retrying...')

        self.sessions[res.session.uuid.hex] = {'session': res.session, 'messages_sent': 0, 'messages_received': 0, 'updates_received': 0}
        self.current_thread = res.session.thread.uuid.hex
        print('Gonna listen')
        self.start_listening(res.session)

    def start_listening(self, session):
        threading.Thread(target=self._listen, args=(session,), daemon=True).start()
        

    def _listen(self, session):
        # Get server updates
        for update in self.connection.ReceiveUpdates(session):
            # Handle update
            self.handle_update(update)
            # Acknowledge
            acknowledgement = chat_pb2.Acknowledgement(
                session = session,
                numUpdatesReceived = self.sessions[session.uuid.hex]['updates_received'],
                numMessagesReceived = self.sessions[session.uuid.hex]['messages_received'],
                numMessagesSent = self.sessions[session.uuid.hex]['messages_sent']
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

            # Listen to new thread
            thread = chat_pb2.Thread(uuid = self.current_thread)
            self.connect(thread)

        # Send message to server
        s = self.sessions[self.thread_to_session(self.current_thread)]
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
        print('Sent message status: ' + str(status.statusCode) + '\n')

    def current_time(self):
        return int(round(time.time() * 1000 * 1000))

    # Return the session uid that belongs to a thread uuid
    def thread_to_session(self, thread_uuid):
        for k, v in self.sessions.items():
            if v['session'].thread.uuid.hex == thread_uuid:
                return k

def run(client):
    while True:
        message = input("")
        client.handle_input(message)
    client.connection_config.connection.close()

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
