import grpc
from proto import chat_pb2
from proto import chat_pb2_grpc
def run():
  with grpc.insecure_channel('localhost:50051') as channel:
    chat_server = chat_pb2_grpc.ChatServerStub(channel)
    default_thread = chat_pb2.Thread()
    connectionResponse = chat_server.Connect(default_thread)
    print(connectionResponse.session.uuid)
    print("Connection successful")

if __name__ == '__main__':
  run()