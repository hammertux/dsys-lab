# Dyconit Chat System

The Dyconit Chat System is a scalable chat system, implemented in Python.

It makes use of these libraries:

- [gRPC](https://grpc.io/docs/quickstart/python/)

## Installation instructions for developers

1. Make sure you have Python 3 installed
2. Make sure you install grpc. Using Pip, you could do so by running: `pip3 install grpcio`

## Proto specification

```proto
syntax = "proto3";

service ChatServer{
  // Required before making other calls to obtain a valid Client object
  rpc Connect(ConnectionStarter) returns (ServerInfo) {}

  // Listen for updates from the server. Consistency is only guaranteed after receiving the first Update.
  // This call must only be done once for a specific Client.
  // Note that consistent order of the updates is guaranteed by gRPC.
  rpc ReceiveUpdates(Client) returns (stream Update) {}

  // Acknowledge updates received from the server, so that the server knows if the connection was dropped.
  // This call returns the ServerTime so that the client can make better estimates of the server time.
  rpc Acknowlegde(Acknowledgement) returns (ServerTime) {}

  // Try to send a message to the chat server. The MessageStatus indicates if it has been accepted.
  // Multiple requests can be done at the same time but consistent ordering will not be guaranteed.
  rpc SendMessage(SentMessage) returns (MessageStatus) {}

  // Send multiple messages to the chat server. Consistent ordering is guaranteed between the messages.
  // Each SentMessage will be matched by a MessageStatus.
  rpc SendMessages(stream SentMessage) returns (stream MessageStatus) {}
}

// Empty message
message ConnectionStarter{

}

// informs the server about which messages where received by a certain client
message Acknowledgement{
  // the client that is sending the acknowledgement
  Client client = 1;
  //indicates to the server how many updates from the stream were already received by the client
  int64 numUpdatesReceived = 2;
  //indicates how many messages the client has sent using SendMessage
  int64 numMessagesSent = 3;
}

message MessageStatus{
  // indicates the status of the message
  StatusCode statusCode = 1;

  //the timestamp at which the messages was accepted
  ServerTime timestamp = 2;

  // indicates the status of a message
  enum StatusCode{
    // the message was received succesfully by the server
    OK = 0;
    // the client does not seem to adhere to the protocol correctly
    // (for example, sending an invalid Client.id)
    CLIENT_ERROR = 1;
    // some other error occurred on the server (similar to HTTP 500)
    INTERNAL_ERROR = 2;
    // too many messages have arrived on the server since the client sent the message
    // or too many messages from the client still need to be accepted by the server (or a combination)
    // the client could retry sending the message when it has received more messages from the server
    ORDER_ERROR = 3;
    // the server has too many messages that have not been sent to all active clients yet
    // to ensure some amount of consistency, this message was rejected
    // the client could try again later
    NUMERICAL_ERROR = 4;
    // it took too long for your message to be sent to the server
    // the client could try again hoping that this time the message will arrive earlier
    STALENESS = 5;
  }
}

// the time as it is on the server
// the client should always make conservative assumptions, when converting it to client time
message ServerTime{
  // timestamp in microseconds
  int64 timestamp = 1;
}

// provides information about the server state
message ServerInfo{
  // The current server time. This is never completely precise because of network latency.
  ServerTime currentTime = 1;
  // The client the server is responding to.
  Client client = 2;
}

message Thread{
  // Uniquely identifies the thread
  string id = 1;
}

message SentMessage{
  // The thread the message should be sent to (optional)
  Thread thread = 1;
  // Contents of the message
  string contents = 2;
  // Time the message was sent
  // The client guarantees that the message was sent after this time
  // (taking into account that received server times could be inaccurate, although the client can make some assumptions about the server's clock)
  ServerTime timestamp = 3; 
  // Indicates the state of the client at the time of sending the message
  Acknowledgement acknowledgement = 4;
}

// Represents an update from the server to the client
// Can contain multiple messages
message Update{
  // Can be used by the client to keep track of the time difference between server and client
  ServerTime currentTime = 1;
  // The server time at which the client should have received updates from the server.
  // Consistency between this client and the server is not guaranteed after this time has passed on the server
  // (unless the expiration time has been updated in the meantime, which will always happen if no messages are dropped).
  ServerTime expirationTime = 2;
  // Chat messages sent by the server to the client
  repeated ReceivedMessage message = 3;
}

message ReceivedMessage{
  // The thread the message was sent on
  Thread thread = 1;
  // The contents of the message
  string contents = 2;
  // The time the message was received on the server
  ServerTime serverTime = 3;
  // The sender of the message
  string sender = 4;
}

message Client{
  // identifies the client to the server
  int64 id = 1;
}
```
