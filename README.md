# Dyconit Chat System

The Dyconit Chat System is a scalable chat system, implemented in Python.

It makes use of these libraries:

- [gRPC](https://grpc.io/docs/quickstart/python/)

## Installation instructions for developers

1. Make sure you have Python 3 installed
2. Make sure you install grpc. Using Pip, you could do so by running: `pip3 install grpcio`

## Proto specification

### Client

```proto
syntax = "proto3";

service ChatClient{
  rpc ReceiveUpdate(Update) returns (Acknowledgement) {}
}

message Acknowledgement{

}

message Thread{
  string identifier = 1;
}

message ServerTime{
  int64 timestamp = 1;
}

message Update{
  // After this time, the client should have received another update from the server
  ServerTime expirationTimestamp = 1;
  // Can be used by the client to keep track of the time difference between server and client
  ServerTime currentTimestamp = 2;
  repeated Message message = 3;
}

message Message{
  Thread thread = 1;
  string contents = 2;
  int64 timestamp = 3;
  string sender = 4;
}
```

### Server

```proto
syntax = "proto3";

service ChatServer{
  rpc Connect(ConnectionInfo) returns (ServerInfo) {}
  rpc SendMessage(Message) returns (MessageStatus) {}
}

message ConnectionInfo{
  string host = 1;
  int32 port = 2;
}

message MessageStatus{
  int32 statusCode = 1;
}

message ServerTime{
  int64 timestamp = 1;
}

message ServerInfo{
  ServerTime serverTime = 1;
  Client client = 2;
}

message Thread{
  string identifier = 1;
}

message Message{
  Thread thread = 1;
  string contents = 2;
  int64 timestamp = 3;
  Client sender = 4;
}

message Client{
  int64 id = 1;
}
```
