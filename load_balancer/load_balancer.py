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
        self.connections = {}

        # Key: Connectioninfo channel
        # Value: List of thread UUID hexes
        self.threads = {}

        # Key: Connectioninfo channel
        # Value: Queue containing requests to that server
        self.message_queues = {}

        self.loads = {}

    def get_thread_connection(self, thread_uuid):
        for channel, threads in self.threads.items():
            if thread_uuid in threads:
                return self.connections[channel]
        return None

    def connection_info_to_channel(self, connectionInfo):
        return connectionInfo.ip + ':' + str(connectionInfo.port)

    def _requester(self, channel):
        while True:
            request = self.message_queues[channel].get()
            print('request sent:', channel, request)
            yield request

    def get_lowest_load(self):
        selected_channel = None
        lowest = None
        for channel, load in self.loads.items():
            if not lowest or lowest > load:
                lowest = load
                selected_channel = channel
        return selected_channel

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
        self.threads[channel] = []
        self.message_queues[channel] = queue.Queue()
        # Add server to request stream
        print(connectionInfo)
        return self._requester(channel)

    def sendLoad(self, Load, context):
        """
        Add load that chat server sent to dictionary and return response
        """
        self.loads[Load.info.ip + ':' + Load.info.port] = Load.cpuLoad
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
            for _, q in self.message_queues.items():
                q.put(load_balancer_pb2.Request(type=load_balancer_pb2.RequestType.LOAD, thread=chat_pb2.Thread()))
            time.sleep(0.5)

            # Create thread on connection with lowest load
            channel = self.get_lowest_load()
            print('lowest: ', channel)
            self.message_queues[channel].put(load_balancer_pb2.Request(type=load_balancer_pb2.RequestType.CREATETHREAD, thread=Thread))

            # Add connection - thread mapping
            self.threads[channel].append(Thread.uuid.hex)

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
    if block:
        server.wait_for_termination()

def stop_serving():
    global server
    server.stop(0)

if __name__ == "__main__":
    serve(True)