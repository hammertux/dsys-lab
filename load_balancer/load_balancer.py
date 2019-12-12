from proto import load_balancer_pb2 # For message construction
from proto import load_balancer_pb2_grpc # For grpc server and service creation

from proto import chat_pb2

import queue
import grpc
import threading
import concurrent.futures
import time

'''
Contains the procedures that can be called remotely by the chat client/server
'''
class LoadBalancerServicer(load_balancer_pb2_grpc.LoadBalancerServerServicer):
    def __init__(self):
        # Key: Connectioninfo channel
        # Value: Connectioninfo object
        self.connections_lock = threading.RLock()
        self.connections = {}

        # Key: thread UUID hex
        # Value: Connectioninfo channel
        self.threads_lock = threading.RLock()
        self.threads = {}

        # Key: Connectioninfo channel
        # Value: Queue containing requests to that server
        self.messages_lock = threading.RLock()
        self.message_queues = {}

        self.loads_lock = threading.RLock()
        self.loads = {}
        self.pongs = []

    def get_thread_connection(self, thread_uuid):
        if thread_uuid in self.threads.keys():
            with self.connections_lock:
                return self.connections[self.threads[thread_uuid]]
        return None

    def connection_info_to_channel(self, connectionInfo):
        return connectionInfo.ip + ':' + str(connectionInfo.port)

    def _requester(self, channel):
        while True:
            request = self.message_queues[channel].get()
            yield request

    def get_lowest_load(self):
        selected_channel = None
        lowest = None
        with self.loads_lock:
            for channel, load in self.loads.items():
                if not lowest or lowest > load:
                    lowest = load
                    selected_channel = channel
        return selected_channel

    def start_pinger(self):
        threading.Thread(target=self._pinger, daemon=True).start()

    def _pinger(self):
        """
        Ping all knows servers every two seconds
        """
        while True:
            self.pongs = []
            with self.messages_lock:
                for _, q in self.message_queues.items():
                    q.put(load_balancer_pb2.Request(type=load_balancer_pb2.RequestType.PING, thread=chat_pb2.Thread()))
            # Wait half a second to receive all answers
            time.sleep(0.5)
            self.handle_pongs()
            time.sleep(2)

    def handle_pongs(self):
        # Check which servers did not send pings
        missing_channels = list(set(self.connections.keys()) - set(self.pongs))
        self.pongs = []
        for channel in missing_channels:
            self.message_queues[channel].put(load_balancer_pb2.Request(type=load_balancer_pb2.RequestType.PING, thread=chat_pb2.Thread()))
        time.sleep(0.5)
        down_channels = list(set(missing_channels) - set(self.pongs))
        for down_channel in down_channels:
            self.handle_server_down(down_channel)

    def handle_server_down(self, down_channel):
        """
        Remove the connection of server that is down and distribute the threads over the other servers
        """
        print('Remapping threads of down server')
        with self.connections_lock:
            del self.connections[down_channel]
        with self.messages_lock:
            del self.message_queues[down_channel]
        channels = list(self.connections.keys())
        if len(channels) > 0:
            i = 0
            with self.threads_lock:
                for thread, channel in self.threads.items():
                    if channel == down_channel:
                        self.threads[thread] = channels[i]
                        i += 1
                        if i == len(channels):
                            i = 0

    ###
    # Remote procedure calls
    ###

    def receiveRequests(self, connectionInfo, context):
        """
        Save connection info of a chat server and start sending requests to it
        """
        # Store server information
        channel = self.connection_info_to_channel(connectionInfo)
        self.connections[channel] = connectionInfo
        self.message_queues[channel] = queue.Queue()
        # Add server to request stream
        print('New server stored:', connectionInfo)
        return self._requester(channel)

    def sendLoad(self, Load, context):
        """
        Add load that chat server sent to dictionary and return response
        """
        with self.loads_lock:
            self.loads[Load.info.ip + ':' + Load.info.port] = Load.cpuLoad
        print('Loads:')
        print(self.loads)
        return load_balancer_pb2.Status(status=load_balancer_pb2.StatusCode.SUCCESS)

    def sendPong(self, Pong, context):
        """
        Send a pong as chat server after receiving a ping request
        """
        self.pongs.append(self.connection_info_to_channel(Pong.info))
        return load_balancer_pb2.Status(status=load_balancer_pb2.StatusCode.SUCCESS)


    def ConnectRequest(self, Thread, context):
        """
        Send the connection info of a server to the client that contains the thread
        """
        print('Client request')
        connection = self.get_thread_connection(Thread.uuid.hex)
        if connection:
            return connection
        else:
            # Get the loads
            with self.messages_lock:
                for _, q in self.message_queues.items():
                    q.put(load_balancer_pb2.Request(type=load_balancer_pb2.RequestType.LOAD, thread=chat_pb2.Thread()))
            time.sleep(0.5)

            # Create thread on connection with lowest load
            channel = self.get_lowest_load()
            self.message_queues[channel].put(load_balancer_pb2.Request(type=load_balancer_pb2.RequestType.CREATETHREAD, thread=Thread))

            # Add thread - channel mapping
            self.threads[Thread.uuid.hex] = channel

            self.loads = {}
            return self.connections[channel]

server = None
def serve(block = False):
    global server
    server = grpc.server(concurrent.futures.ThreadPoolExecutor(max_workers=10))
    servicer = LoadBalancerServicer()
    load_balancer_pb2_grpc.add_LoadBalancerServerServicer_to_server(servicer, server)
    server.add_insecure_port('[::]:50050')
    server.start()

    servicer.start_pinger()

    if block:
        server.wait_for_termination()

def stop_serving():
    global server
    server.stop(0)

if __name__ == "__main__":
    serve(True)