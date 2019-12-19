# Dyconit Chat System

The Dyconit Chat System is a scalable chat system, implemented in Python.

It makes use of these libraries:

- [gRPC](https://grpc.io/docs/quickstart/python/)

## Installation instructions for developers

1. Make sure you have Python 3 installed
2. Make sure you install grpc. Using Pip, you could do so by running: `pip3 install grpcio`

## Starting the Load balancer:
`python3 run_load_balancer.py`

## Starting the server:
`python3 run_server.py`

## Using the client:

`python3 run_client.py <username>` spawns a new client which by default will join the global chat. Messages can be sent to the global chat or by specifying a discussion thread:

`<message>` goes to global chat

`<message> | <disc. thread>` goes to the specified discussion thread

`<message> | global` to go back chatting in the global chat room


