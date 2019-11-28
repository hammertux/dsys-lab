# Generated by the gRPC Python protocol compiler plugin. DO NOT EDIT!
import grpc

from . import chat_pb2 as chat__pb2


class ChatServerStub(object):
  # missing associated documentation comment in .proto file
  pass

  def __init__(self, channel):
    """Constructor.

    Args:
      channel: A grpc.Channel.
    """
    self.Connect = channel.unary_unary(
        '/ChatServer/Connect',
        request_serializer=chat__pb2.Thread.SerializeToString,
        response_deserializer=chat__pb2.ConnectionResponse.FromString,
        )
    self.ReceiveUpdates = channel.unary_stream(
        '/ChatServer/ReceiveUpdates',
        request_serializer=chat__pb2.Session.SerializeToString,
        response_deserializer=chat__pb2.Update.FromString,
        )
    self.Acknowlegde = channel.unary_unary(
        '/ChatServer/Acknowlegde',
        request_serializer=chat__pb2.Acknowledgement.SerializeToString,
        response_deserializer=chat__pb2.ServerTime.FromString,
        )
    self.SendMessage = channel.unary_unary(
        '/ChatServer/SendMessage',
        request_serializer=chat__pb2.SentMessage.SerializeToString,
        response_deserializer=chat__pb2.MessageStatus.FromString,
        )
    self.SendMessages = channel.stream_stream(
        '/ChatServer/SendMessages',
        request_serializer=chat__pb2.SentMessage.SerializeToString,
        response_deserializer=chat__pb2.MessageStatus.FromString,
        )


class ChatServerServicer(object):
  # missing associated documentation comment in .proto file
  pass

  def Connect(self, request, context):
    """Required before making other calls to obtain a valid Client object
    If a client wants to listen to multiple threads, it should make multiple connections
    """
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')

  def ReceiveUpdates(self, request, context):
    """Listen for updates from the server. Consistency is only guaranteed after receiving the first Update.
    This call must only be done once for a specific Client.
    Note that consistent order of the updates is guaranteed by gRPC.
    Messages that were sent before ReceiveUpdates was called may or may not be included.
    """
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')

  def Acknowlegde(self, request, context):
    """Acknowledge updates received from the server, so that the server knows if the connection was dropped.
    This call returns the ServerTime so that the client can make better estimates of the server time.
    """
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')

  def SendMessage(self, request, context):
    """Try to send a message to the chat server. The MessageStatus indicates if it has been accepted.
    Multiple requests can be done at the same time but consistent ordering will not be guaranteed.
    """
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')

  def SendMessages(self, request_iterator, context):
    """Send multiple messages to the chat server. Consistent ordering is guaranteed between the messages.
    Each SentMessage will be matched by a MessageStatus.
    """
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')


def add_ChatServerServicer_to_server(servicer, server):
  rpc_method_handlers = {
      'Connect': grpc.unary_unary_rpc_method_handler(
          servicer.Connect,
          request_deserializer=chat__pb2.Thread.FromString,
          response_serializer=chat__pb2.ConnectionResponse.SerializeToString,
      ),
      'ReceiveUpdates': grpc.unary_stream_rpc_method_handler(
          servicer.ReceiveUpdates,
          request_deserializer=chat__pb2.Session.FromString,
          response_serializer=chat__pb2.Update.SerializeToString,
      ),
      'Acknowlegde': grpc.unary_unary_rpc_method_handler(
          servicer.Acknowlegde,
          request_deserializer=chat__pb2.Acknowledgement.FromString,
          response_serializer=chat__pb2.ServerTime.SerializeToString,
      ),
      'SendMessage': grpc.unary_unary_rpc_method_handler(
          servicer.SendMessage,
          request_deserializer=chat__pb2.SentMessage.FromString,
          response_serializer=chat__pb2.MessageStatus.SerializeToString,
      ),
      'SendMessages': grpc.stream_stream_rpc_method_handler(
          servicer.SendMessages,
          request_deserializer=chat__pb2.SentMessage.FromString,
          response_serializer=chat__pb2.MessageStatus.SerializeToString,
      ),
  }
  generic_handler = grpc.method_handlers_generic_handler(
      'ChatServer', rpc_method_handlers)
  server.add_generic_rpc_handlers((generic_handler,))