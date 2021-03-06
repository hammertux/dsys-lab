# Generated by the gRPC Python protocol compiler plugin. DO NOT EDIT!
import grpc

from . import chat_pb2 as chat__pb2
from . import load_balancer_pb2 as load__balancer__pb2


class LoadBalancerServerStub(object):
  # missing associated documentation comment in .proto file
  pass

  def __init__(self, channel):
    """Constructor.

    Args:
      channel: A grpc.Channel.
    """
    self.receiveRequests = channel.unary_stream(
        '/LoadBalancerServer/receiveRequests',
        request_serializer=load__balancer__pb2.ConnectionInfo.SerializeToString,
        response_deserializer=load__balancer__pb2.Request.FromString,
        )
    self.sendLoad = channel.unary_unary(
        '/LoadBalancerServer/sendLoad',
        request_serializer=load__balancer__pb2.Load.SerializeToString,
        response_deserializer=load__balancer__pb2.Status.FromString,
        )
    self.sendPong = channel.unary_unary(
        '/LoadBalancerServer/sendPong',
        request_serializer=load__balancer__pb2.Pong.SerializeToString,
        response_deserializer=load__balancer__pb2.Status.FromString,
        )
    self.ConnectRequest = channel.unary_unary(
        '/LoadBalancerServer/ConnectRequest',
        request_serializer=chat__pb2.Thread.SerializeToString,
        response_deserializer=load__balancer__pb2.ConnectionInfo.FromString,
        )


class LoadBalancerServerServicer(object):
  # missing associated documentation comment in .proto file
  pass

  def receiveRequests(self, request, context):
    """Can be used for the chat server to connect to the load balancer
    Receives requests either asking to create a thread, or for the chat server to send its load
    """
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')

  def sendLoad(self, request, context):
    """Used for the chat server to send its load to the load balancer
    """
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')

  def sendPong(self, request, context):
    """Send pong to the load balancer after receiving a ping
    """
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')

  def ConnectRequest(self, request, context):
    """Client can request to connect to a thread
    The load balancer will return the server information to which the client should connect
    """
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')


def add_LoadBalancerServerServicer_to_server(servicer, server):
  rpc_method_handlers = {
      'receiveRequests': grpc.unary_stream_rpc_method_handler(
          servicer.receiveRequests,
          request_deserializer=load__balancer__pb2.ConnectionInfo.FromString,
          response_serializer=load__balancer__pb2.Request.SerializeToString,
      ),
      'sendLoad': grpc.unary_unary_rpc_method_handler(
          servicer.sendLoad,
          request_deserializer=load__balancer__pb2.Load.FromString,
          response_serializer=load__balancer__pb2.Status.SerializeToString,
      ),
      'sendPong': grpc.unary_unary_rpc_method_handler(
          servicer.sendPong,
          request_deserializer=load__balancer__pb2.Pong.FromString,
          response_serializer=load__balancer__pb2.Status.SerializeToString,
      ),
      'ConnectRequest': grpc.unary_unary_rpc_method_handler(
          servicer.ConnectRequest,
          request_deserializer=chat__pb2.Thread.FromString,
          response_serializer=load__balancer__pb2.ConnectionInfo.SerializeToString,
      ),
  }
  generic_handler = grpc.method_handlers_generic_handler(
      'LoadBalancerServer', rpc_method_handlers)
  server.add_generic_rpc_handlers((generic_handler,))
