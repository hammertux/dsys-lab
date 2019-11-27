init:
	python3 -m pip install -r requirements.txt

protoc:
	python3 -m grpc_tools.protoc chat.proto --python_out=proto --grpc_python_out=proto --proto_path=.
	
	# Not the nicest solution, but it works
	sed 's/import chat_pb2 as chat__pb2/from . import chat_pb2 as chat__pb2/g' proto/chat_pb2_grpc.py > proto/chat_pb2_grpc2.py
	mv proto/chat_pb2_grpc2.py proto/chat_pb2_grpc.py

server/chat_pb2_grpc.py: protoc
server/chat_pb2.py: protoc
client/chat_pb2.py: protoc
	