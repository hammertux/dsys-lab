from proto import chat_pb2_grpc # Contains the code necessary for creating the GRPC server and instantiating the service
from proto import chat_pb2 # Contains the code necessary for constructing messages
from .session import SessionMessage, SessionStore
import uuid
from . import time_utils
from . import message as message_mod
import queue
import grpc
import threading
import concurrent.futures
import time
from pprint import pprint
from .acknowledgement_tracker import AcknowledgementTracker, MultiAcknowledgeable
from .consistency_requirement import CompositeRequirement, OrderEnforcer
from .numerical_error import NumericalErrorLimiter, NumericalError
from .order_error import OrderErrorLimiter, OrderError
from .queue_generator import QueueGenerator
import itertools

def string_to_uuid_or_default(string, default):
  try:
    return uuid.UUID(string)
  except:
    return default

def create_connection_response(currentTime, session, thread_uuid):
  result = chat_pb2.ConnectionResponse()
  result.session.uuid.hex = session.uuid.hex
  result.session.thread.uuid.hex = thread_uuid.hex
  return result

class ThreadConfiguration:
  def __init__(self, max_numerical_error, max_order_error, max_staleness):
    self.max_numerical_error = max_numerical_error
    self.max_order_error = max_order_error
    self.max_staleness = max_staleness

"""Implements ChatServerServicer. This class contains all the procedures that can be accessed by RPC's.
It delegates most task to the thread specific servicer"""
class ChatServicer(chat_pb2_grpc.ChatServerServicer):
  def __init__(self, thread_configuration):
    self.threads = {}
    self.default_uuid = uuid.UUID(int=0)
    self.thread_configuration = thread_configuration


  def add_default_thread(self, thread_configuration):
    self.add_thread(self.default_uuid, thread_configuration)


  def add_thread(self, uuid, thread_configuration):
    self.threads[uuid] = ThreadServicer(uuid, thread_configuration)
    self.threads[uuid].start_broadcasting()


  def __get_or_create_thread(self, uuid):
    if (not uuid in self.threads):
      self.add_thread(uuid, self.thread_configuration)
    return self.threads[uuid]


  def lookup_thread(self, thread):
    return self.__get_or_create_thread(self.parse_uuid(thread.uuid.hex))
  
  def parse_uuid(self, uuid_hex):
    return string_to_uuid_or_default(uuid_hex, self.default_uuid)


  """Generates a new client ID and returns it to the caller."""
  def Connect(self, connectionRequest, context):
    # defer the processing to the appropriate servicer
    return self.lookup_thread(connectionRequest.thread).Connect(connectionRequest.name) # defer connections to the thread servicer


  def ReceiveUpdates(self, session, context):
    # defer the processing to the appropriate servicer
    return self.lookup_thread(session.thread).ReceiveUpdates(uuid.UUID(session.uuid.hex))


  def Acknowlegde(self, acknowledgement, context):
    # defer the processing to the appropriate servicer
    self.lookup_thread(acknowledgement.session.thread).Acknowlegde(acknowledgement)

    # Response is always just the server time
    return chat_pb2.ServerTime(timestamp = time_utils.current_server_time())
  

  def __send_message(self, sentMessage):
    # defer the processing to the appropriate servicer
    return self.lookup_thread(sentMessage.acknowledgement.session.thread).SendMessage(sentMessage)


  def SendMessage(self, sentMessage, context):
    return self.__send_message(sentMessage)


  def SendMessages(self, sentMessages, context):
    for sentMessage in sentMessages:
      yield self.__send_message(sentMessage)

class ThreadServicer(AcknowledgementTracker):
  def __init__(self, uuid, thread_configuration):
    AcknowledgementTracker.__init__(self)
    self.session_store = SessionStore()
    self.uuid = uuid
    # the broadcast queue contains messages that still need to be broadcasted to individual threads
    # while using its lock, do not lock the commit queue (to avoid deadlocks)
    self.broadcast_queue = queue.Queue()
    self.broadcast_queue_generator = QueueGenerator(self.broadcast_queue)
    self.numerical_error_limiter = NumericalErrorLimiter(thread_configuration.max_numerical_error)
    self.order_error_limiter = OrderErrorLimiter(thread_configuration.max_order_error)
    self.order_enforcer = OrderEnforcer()
    self.message_consistency = CompositeRequirement(CompositeRequirement(self.numerical_error_limiter, self.order_error_limiter), self.order_enforcer)
    self.commit_number_generator = itertools.count()
    self.last_commit_number = next(self.commit_number_generator)
    self.max_staleness_in_send_message = thread_configuration.max_staleness * 1000 * 1000

  def _after_acknowledge(self, count):
    self.numerical_error_limiter.decrease_numerical_error_by(count)

  def Connect(self, name):
    print('New connection')
    session = self.session_store.create(self, name)
    self.order_enforcer.commit(session)
    return create_connection_response(time_utils.current_server_time(), session, self.uuid)
  
  def ReceiveUpdates(self, session_uuid):
    # defer the processing to the appropriate session object
    return self.session_store.retrieve(session_uuid).ReceiveUpdates()

  def Acknowlegde(self, acknowledgement):
    # update the acknowledgement count in the session
    session = self.session_store.retrieve_by_hex(acknowledgement.session.uuid.hex)
    session.Acknowledge(acknowledgement)
  
  def __create_ok_message_status(self, message):
    return chat_pb2.MessageStatus(
      statusCode = chat_pb2.MessageStatusCode.OK,
      messageTime = chat_pb2.ServerTime(timestamp = message.commit_time)
    )

  def __create_numerical_error_message_status(self):
    return chat_pb2.MessageStatus(
      statusCode = chat_pb2.MessageStatusCode.NUMERICAL_ERROR,
      messageTime = chat_pb2.ServerTime(timestamp = time_utils.current_server_time())
    )

  def __create_order_error_message_status(self):
    return chat_pb2.MessageStatus(
      statusCode = chat_pb2.MessageStatusCode.ORDER_ERROR,
      messageTime = chat_pb2.ServerTime(timestamp = time_utils.current_server_time())
    )
  
  def generate_commit_number(self):
    self.last_commit_number = 1
    while True:
      self.last_commit_number += 1
      yield self.last_commit_number

  # called right after a message is committed
  # no other messages will be committed until this function completes
  # which means that commit ordering is preserved
  def __on_message_commit(self, message):
    self.last_commit_number = message.commit_number
    # non-blocking because broadcast and unacknowledged queue do not have a maximum size
    # it could still be that it needs to wait to acquire the lock though
    # this function is called while the commit queue is locked, so to avoid deadlock,
    # it is important that the broadcast queue lock is not in use by anyone trying to lock the commit queue
    self.broadcast_queue.put(message)

  def SendMessage(self, sentMessage):
    # convert the raw chat_pb2.SentMessage into a message_mod.Message instance
    sender_session = self.session_store.retrieve_by_hex(sentMessage.acknowledgement.session.uuid.hex)
    sender_session.Acknowledge(sentMessage.acknowledgement)
    message = message_mod.Message(
      sentMessage,
      commit_deadline = sentMessage.timestamp.timestamp + self.max_staleness_in_send_message,
      on_commit = self.__on_message_commit,
      sender_session = sender_session,
      commit_number_generator = self.commit_number_generator
    )
    # try to commit the message
    try:
      self.message_consistency.commit(message, time_utils.to_python_time(message.time_left_before_commit_deadline()))
      return self.__create_ok_message_status(message)
    # if the message could not be committed due to the numerical error being too high
    except NumericalError:
      return self.__create_numerical_error_message_status()
    except OrderError:
      return self.__create_order_error_message_status()
    # if the message could not be committed due to the message having arrived too late
    except message_mod.CommitTooLate as e:
      return e.to_message_status()

  def start_broadcasting(self):
    # create the broadcast thread as a daemon thread
    # such that as soon as the server stops, this thread should stop as well
    self.broadcast_thread = threading.Thread(target=self.broadcast_messages, daemon=True)
    self.broadcast_thread.start()

  def broadcast_messages(self):
    for message in self.broadcast_queue_generator.generate(): # waits for a new message if neccessary
      # make a copy of the sessions so that new sessions can be added while we're broadcasting
      sessions = list(self.session_store.dict.values())
      # make sure acknowledgements of this message are tracked
      acknowledgeable = MultiAcknowledgeable(len(sessions))
      self.add_unacknowledged(acknowledgeable)
      # queue it for all sessions subscribed to this thread
      for session in sessions:
        session.message_queue.put(SessionMessage(message, acknowledgeable))

server = None
def serve(block = False, max_numerical_error_global = 10, max_order_error_global = 5, max_staleness_global = 10, max_numerical_error_other = 2, max_order_error_other = 1, max_staleness_other = 10):
  global server
  server = grpc.server(concurrent.futures.ThreadPoolExecutor(max_workers=10))
  servicer = ChatServicer(ThreadConfiguration(max_numerical_error_other, max_order_error_other, max_staleness_other))
  servicer.add_default_thread(ThreadConfiguration(max_numerical_error_global, max_order_error_other, max_staleness_global))
  chat_pb2_grpc.add_ChatServerServicer_to_server(servicer, server)
  server.add_insecure_port('[::]:50051')
  server.start()
  if block:
    server.wait_for_termination()

def stop_serving():
  global server
  server.stop(0)
