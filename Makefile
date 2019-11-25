init:
	python3 -m pip install -r requirements.txt

protoc:
	python3 -m grpc_tools.protoc chat.proto --python_out=server --grpc_python_out=server --proto_path=.
	cp server/chat_pb2.py client/chat_pb2.py

server/chat_pb2_grpc.py: protoc
server/chat_pb2.py: protoc
client/chat_pb2.py: protoc
	