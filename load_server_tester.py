import os
import time
import sys
import threading
import random

from time import gmtime, strftime

import grpc
from proto import load_balancer_pb2
from proto import load_balancer_pb2_grpc

# username as param
if __name__ == "__main__":
    # Load balancer info
    ip = 'localhost'
    port = 50050

    cport = 5005 + random.randint(0, 9)
    info = load_balancer_pb2.ConnectionInfo(ip='localhost', port=str(cport))

    load_balancer_channel = grpc.insecure_channel(ip + ':' + str(port))
    load_balancer_connection = load_balancer_pb2_grpc.LoadBalancerServerStub(load_balancer_channel)
    for req in load_balancer_connection.receiveRequests(info):
        print(req.type)
        if req.type == 1:
            status = load_balancer_connection.sendLoad(load_balancer_pb2.Load(cpuLoad=random.randint(0, 9), networkLoad=2, info=info))
            print(status)
