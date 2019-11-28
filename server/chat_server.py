from proto import chat_pb2_grpc # Contains the code necessary for creating the GRPC server and instantiating the service
from proto import chat_pb2 # Contains the code necessary for constructing messages
from . import session # Keeps track of which clients are connected
import uuid
from . import time_utils
from . import message as message_mod
import queue
import grpc
import threading
import concurrent.futures
import time
from pprint import pprint

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

"""Implements ChatServerServicer. This class contains all the procedures that can be accessed by RPC's.
It delegates most task to the thread specific servicer"""
class ChatServicer(chat_pb2_grpc.ChatServerServicer):
  def __init__(self):
    self.threads = {}
    self.default_uuid = uuid.UUID(int=0)


  def add_default_thread(self):
    self.add_thread(self.default_uuid)


  def add_thread(self, uuid):
    self.threads[uuid] = ThreadServicer(uuid)
    self.threads[uuid].start_broadcasting()


  def __get_or_create_thread(self, uuid):
    if (not uuid in self.threads):
      self.add_thread(uuid)
    return self.threads[uuid]


  def lookup_thread(self, thread):
    return self.__get_or_create_thread(self.parse_uuid(thread.uuid.hex))
  
  def parse_uuid(self, uuid_hex):
    return string_to_uuid_or_default(uuid_hex, self.default_uuid)


  """Generates a new client ID and returns it to the caller."""
  def Connect(self, thread, context):
    # defer the processing to the appropriate servicer
    return self.lookup_thread(thread).Connect() # defer connections to the thread servicer


  def ReceiveUpdates(self, session, context):
    # defer the processing to the appropriate servicer
    return self.lookup_thread(session.thread).ReceiveUpdates(uuid.UUID(session.uuid.hex))


  def Acknowlegde(self, acknowledgement, context):
    # defer the processing to the appropriate servicer
    self.lookup_thread(acknowledgement.session.thread).Acknowlegde(acknowledgement)

    # Response is always just the server time
    server_time = chat_pb2.ServerTime()
    server_time.timestamp = time_utils.current_server_time()
    return server_time
  

  def __send_message(self, sentMessage):
    # defer the processing to the appropriate servicer
    return self.lookup_thread(sentMessage.acknowledgement.session.thread).SendMessage(sentMessage)


  def SendMessage(self, sentMessage, context):
    return self.__send_message(sentMessage)


  def SendMessages(self, sentMessages, context):
    for sentMessage in sentMessages:
      yield self.__send_message(sentMessage)

class ThreadServicer:
  def __init__(self, uuid):
    self.session_store = session.SessionStore()
    self.uuid = uuid
    self.broadcast_queue = queue.Queue()
    self.max_wait_in_send_message_in_seconds = 1

  def Connect(self):
    session = self.session_store.create()
    print('New user connection')
    return create_connection_response(time_utils.current_server_time(), session, self.uuid)
  
  def ReceiveUpdates(self, session_uuid):
    # defer the processing to the appropriate session object
    threading.current_thread.daemon = True
    return self.session_store.retrieve(session_uuid).ReceiveUpdates()

  def Acknowlegde(self, acknowledgement):
    # defer the processing to the appropriate session object
    self.session_store.retrieve_by_hex(acknowledgement.session.uuid.hex).Acknowledge(acknowledgement)

  def SendMessage(self, sentMessage):
    # parse the sent message into another format
    message = message_mod.Message(sentMessage)

    message_status = chat_pb2.MessageStatus()
    try:
      # try putting the message in the broadcast queue
      self.broadcast_queue.put(message, True, self.max_wait_in_send_message_in_seconds)
      # set the time of the message to the time it was accepted
      message.server_time = time_utils.current_server_time()
      # initialization is now complete
      message.complete_initalization()
      
      
      # put the information into the message status
      message_status.messageTime.timestamp = message.server_time
      message_status.statusCode = chat_pb2.MessageStatusCode.OK
    
    # if there was no space in the queue left and the timer ran out
    except queue.Full:
      # provide information about the failure to the client
      message_status.status_code = chat_pb2.MessageStatusCode.NUMERICAL_ERROR
      message_status.messageTime.timestamp = time_utils.current_server_time()

    return message_status

  def start_broadcasting(self):
    # create the broadcast thread as a daemon thread
    # such that as soon as the server stops, this thread should stop as well
    self.broadcast_thread = threading.Thread(target=self.broadcast_messages, daemon=True)
    self.broadcast_thread.start()

  def broadcast_messages(self):
    while True:
      # wait for a new message if neccessary
      message = self.broadcast_queue.get()
      # queue it for all sessions subscribed to this thread
      for session in self.session_store.sessions.values():
        session.messageQueue.put(message)

server = None
def serve(block = False):
  global server
  server = grpc.server(concurrent.futures.ThreadPoolExecutor(max_workers=10))
  servicer = ChatServicer()
  chat_pb2_grpc.add_ChatServerServicer_to_server(servicer, server)
  server.add_insecure_port('[::]:50051')
  server.start()
  if block:
    server.wait_for_termination()

def stop_serving():
  global server
  server.stop(0)
