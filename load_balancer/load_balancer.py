from proto import load_balancer_pb2 # For message construction
from proto import load_balancer_pb2_grpc # For grpc server and service creation

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
        pass

    ###
    # Remote procedure calls
    ###
    def receiveRequests(self, connectionInfo, context):
        pass

    def sendLoad(self, Load, context):
        pass

    def ConnectRequest(self, Thread, context):
        # placeholder test
        return load_balancer_pb2.ConnectionInfo(ip='localhost', port='50051')

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