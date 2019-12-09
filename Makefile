init:
	python3 -m pip install -r requirements.txt

protoc:
	python3 -m grpc_tools.protoc chat.proto --python_out=proto_server --grpc_python_out=proto_server --proto_path=.

	# Not the nicest solution, but it works
	sed 's/import chat_pb2 as chat__pb2/from . import chat_pb2 as chat__pb2/g' proto_server/chat_pb2_grpc.py > proto_server/chat_pb2_grpc2.py
	mv proto_server/chat_pb2_grpc2.py proto_server/chat_pb2_grpc.py

server/chat_pb2_grpc.py: protoc
server/chat_pb2.py: protoc
client/chat_pb2.py: protoc
