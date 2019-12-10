import os
import time
import sys
import threading
import queue
import csv
import collections
import uuid

from time import gmtime, strftime
import datetime

import grpc
from proto import chat_pb2
from proto import chat_pb2_grpc
from proto import load_balancer_pb2
from proto import load_balancer_pb2_grpc

class Client:
    '''
    Params:
        - Username
        - Load balancer ipf
        - Load balancer port
    '''
    def __init__(self, username, ip, port):
        self.username = username

        load_balancer_channel = grpc.insecure_channel(ip + ':' + str(port))
        self.load_balancer_connection = load_balancer_pb2_grpc.LoadBalancerServerStub(load_balancer_channel)

        # Key: Channel
        # Value: Connection to that channel
        self.connections = {}

        # Key: Channel
        # Value: List of thread uuid hex that belong to that server connection
        self.connection_threads = {}

        # Key: Channel
        # Value: Message queue
        self.message_queues = {}

        self.default_thread = chat_pb2.Thread(uuid=chat_pb2.UUID(hex=uuid.UUID(int=0).hex))
        self.current_thread = None
        self.global_uuid = None

        with open('client_log.csv', 'w', newline='') as file:
            logger = csv.writer(file)
            # action: 0 = message sent, 1 = message received, 2 = session expired
            logger.writerow(['timestamp', 'session_id', 'action'])

        # Key: session uuid hex
        # Value: dict(session, messages_sent, messages_received, updates_received, expiration_timer)
        self.sessions = {}

    def get_connection(self, thread):
        info = self.load_balancer_connection.ConnectRequest(thread)
        return info.ip + ':' + str(info.port)

    def create_server_connection(self, channel, thread):
        grpc_channel = grpc.insecure_channel(channel)
        connection = chat_pb2_grpc.ChatServerStub(grpc_channel)
        self.connections[channel] = connection
        self.connection_threads[channel] = [thread.uuid.hex]
        self.message_queues[channel] = queue.Queue()

    def connect(self, thread=None):
        tries = 0
        while True:
            if thread == None:
                thread = self.default_thread
            try:
                connection_request = chat_pb2.ConnectionRequest(thread=thread, name=self.username)
                connection = self.thread_to_connection(thread.uuid.hex)
                res = connection.Connect(connection_request)
                break
            except:
                if tries < 5:
                    time.sleep(2)
                    tries += 1
                else:
                    s = self.sessions[self.thread_to_session(thread.uuid.hex)]['session']
                    self.handle_server_down(s)
                    break

        self.start_sender(connection)

        self.sessions[res.session.uuid.hex] = {'session': res.session, 'messages_sent': 0, 'messages_received': 0, 'updates_received': 0, 'expiration_timer': None}
        self.current_thread = res.session.thread.uuid.hex
        if thread == self.default_thread:
            self.global_uuid = self.current_thread
        print('Listening to new thread')
        self.start_listening(res.session)

    def start_sender(self, connection):
        threading.Thread(target=self._sender, args=(connection,), daemon=True).start()

    def _sender(self, connection):
        try:
            for status in connection.SendMessages(self.__open_messages(self.connection_to_channel(connection))):
                print(status.statusCode)
        except:
            return

    def __open_messages(self, channel):
        while True:
            message = self.message_queues[channel].get()
            yield message

    def start_listening(self, session):
        threading.Thread(target=self._listen, args=(session,), daemon=True).start()

    def _listen(self, session):
        connection = self.thread_to_connection(session.thread.uuid.hex)
        # Get server updates
        try:
            for update in connection.ReceiveUpdates(session):
                # Log update
                self.log(session.uuid.hex, 1)
                # Handle update
                self.handle_update(session, update)
                # Acknowledge
                acknowledgement = chat_pb2.Acknowledgement(
                    session = session,
                    numUpdatesReceived = self.sessions[session.uuid.hex]['updates_received'],
                    numMessagesReceived = self.sessions[session.uuid.hex]['messages_received'],
                    numMessagesSent = self.sessions[session.uuid.hex]['messages_sent']
                )
                timestamp = connection.Acknowlegde(acknowledgement)
        except:
            self.handle_server_down(session)
            return

    def handle_server_down(self, session):
        print('Server down')
        thread_uuid = session.thread.uuid.hex
        old_channel = self.thread_to_channel(thread_uuid)
        # Create new mappings
        channel = self.get_connection(session.thread)
        if channel == old_channel:
            time.sleep(2)
            channel = self.get_connection(session.thread)
        self.create_connection_or_add_thread(channel, session.thread)
        self.connect(session.thread)
        # Add remaining messages to new queue
        self.handle_remaining_messages(session, old_channel)
        # Delete old mappings
        del self.sessions[session.uuid.hex]
        del self.connections[old_channel]
        del self.connection_threads[old_channel]
    
    def handle_remaining_messages(self, session, old_channel):
        # Get messages going to that server
        for message in self.message_queues[old_channel].get():
            # Get channel for that message and put it in the queue
            channel = self.thread_to_channel(session.thread.uuid.hex)
            self.create_message(message, channel, session.thread.uuid.hex)

    def handle_update(self, session, update):
        current_time = self.current_time()
        expiration_time = (update.expirationTime.timestamp - current_time) / 1000000
        self.session_expiration_warning(session.uuid.hex, expiration_time)

        self.sessions[session.uuid.hex]['updates_received'] += 1

        for msg in update.message:
            self.sessions[session.uuid.hex]['messages_received'] += 1
            self.display(msg)

    def display(self, msg):
        time = str(msg.serverTime.timestamp)
        formatted_time = datetime.datetime.fromtimestamp(int(time) / 1000 / 1000).strftime('%c')
        thread = str(msg.thread.uuid.hex)
        id = str(msg.uuid.hex)
        suffix = ''
        if thread == self.global_uuid:
            thread = 'global'
            suffix = ' | ' + id

        print(formatted_time + ' | ' + thread + ' | ' + msg.sender + ': ' + msg.contents + suffix + "\n")

    def handle_input(self, user_input):
        # Get thread
        msg = user_input
        in_split = user_input.split(' ')
        channel = None
        if len(in_split) > 1 and in_split[-2] == '|':
            self.current_thread = in_split[-1]
            if self.current_thread == 'global':
                self.current_thread = self.global_uuid

            msg = ' '.join(in_split[:-2])

            # Listen to new thread if no session has been created
            if not self.thread_to_session(self.current_thread):
                uuid = chat_pb2.UUID(hex=str(self.current_thread))
                thread = chat_pb2.Thread(uuid = uuid)

                channel = self.get_connection(thread)
                self.create_connection_or_add_thread(channel, thread)
                self.connect(thread)

        # Create message and put it in the right queue
        self.create_message(msg, channel)
    
    def create_message(self, msg, channel, thread_uuid=None):
        if not thread_uuid:
            s_id = self.thread_to_session(self.current_thread)
        else:
            s_id = self.thread_to_session(thread_uuid)
        s = self.sessions[s_id]
        s['messages_sent'] += 1
        acknowledgement = chat_pb2.Acknowledgement(
            session = s['session'],
            numUpdatesReceived = s['updates_received'],
            numMessagesReceived = s['messages_received'],
            numMessagesSent = s['messages_sent']
        )
        msg_obj = chat_pb2.SentMessage(
            acknowledgement=acknowledgement,
            contents=msg,
            timestamp=chat_pb2.ServerTime(timestamp=self.current_time())
        )
        if not channel:
            channel = self.thread_to_channel(self.current_thread)
        self.message_queues[channel].put(msg_obj)
        self.log(s_id, 0)

    def create_connection_or_add_thread(self, channel, thread):
        if channel not in self.connections.keys():
            self.create_server_connection(channel, thread)
        else:
            self.connection_threads[channel].append(thread.uuid.hex)

    def session_expiration_warning(self, session_id, time):
        if self.sessions[session_id]['expiration_timer']:
            timer = self.sessions[session_id]['expiration_timer']
            timer.cancel()
        timer = threading.Timer(time, self._show_session_expiration, [session_id])
        self.sessions[session_id]['expiration_timer'] = timer
        timer.start()

    def _show_session_expiration(self, id):
        self.log(id, 2)
        print('Consistency not guaranteed for session: ' + str(id))

    def log(self, session, action):
        '''
        action: 0 = message sent, 1 = message received, 2 = session expired
        '''
        time = self.current_time()
        with open('client_log.csv', 'a', newline='') as file:
            logger = csv.writer(file)
            # action: 0 = message sent, 1 = message received, 2 = session expired
            logger.writerow([time, session, action])

    def current_time(self):
        return int(round(time.time() * 1000 * 1000))

    # Return the session uid that belongs to a thread uuid
    def thread_to_session(self, thread_uuid):
        for k, v in self.sessions.items():
            if v['session'].thread.uuid.hex == thread_uuid:
                return k
        return None

    def thread_to_connection(self, thread_uuid):
        for channel, threads in self.connection_threads.items():
            if thread_uuid in threads:
                return self.connections[channel]

    def thread_to_channel(self, thread_uuid):
        for channel, threads in self.connection_threads.items():
            if thread_uuid in threads:
                return channel

    def connection_to_channel(self, connection):
        for channel, c in self.connections.items():
            if connection == c:
                return channel

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
    port = 50050
    client = Client(username, ip, port)
    channel = client.get_connection(client.default_thread)
    client.create_server_connection(channel, client.default_thread)
    client.connect()
    print('Connected to server with session {}\nWelcome to the chat {}'.format(list(client.sessions)[0], client.username))
    run(client)
