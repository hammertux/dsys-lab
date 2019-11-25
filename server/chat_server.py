import chat_pb2_grpc # Contains the code necessary for creating the GRPC server and instantiating the service
import chat_pb2 # Contains the code necessary for constructing messages
import session # Keeps track of which clients are connected
import uuid
import time_utils

def string_to_uuid_or_default(string, default):
  try:
    return uuid.UUID(string)
  except:
    return default

"""Implements ChatServerServicer. This class contains all the procedures that can be accessed by RPC's"""
class ChatServicer(chat_pb2_grpc.ChatServerServicer):
  def __init__(self):
    self.threads = {}
    self.default_uuid = uuid.UUID(0)

  def add_default_thread(self):
    self.add_thread(self.default_uuid)

  def add_thread(self, uuid):
    self.threads[uuid] = ThreadServicer(uuid)

  def get_or_create_thread(self, uuid):
    if (not uuid in self.threads):
      self.add_thread(uuid)
    return self.threads[uuid]

  """Generates a new client ID and returns it to the caller."""
  def Connect(self, thread):
    thread_uuid = string_to_uuid_or_default(thread.uuid.hex, self.default_uuid)
    response = chat_pb2.ConnectionResponse()
    response.session = self.get_or_create_thread(thread_uuid).Connect()
    response.currentTime = time_utils.current_server_time()
    return response

  def ReceiveUpdates(self, session):
    return self.threads[session.thread.uuid.uuid].ReceiveUpdates(session.uuid)

class ThreadServicer:
  def __init__(self, uuid):
    self.session_store = session.SessionStore()
    self.uuid = uuid
    self.expirationTime = time_utils.current_server_time()
    self.sessionLength = 10*1000*1000 # session length in microseconds

  def session_to_chat_pb2(self, session):
    result = chat_pb2.Session()
    result.uuid.hex = session.uuid.hex
    result.thread_uuid_hex = self.uuid.hex
    return result

  def Connect(self):
    return self.session_to_chat_pb2(self.session_store.create())
  
  def ReceiveUpdates(self, session_uuid):
    session = self.session_store.retrieve(session_uuid)
    while True:
      message = session.queue.get() # blocks until there are elements in the queue
      update = chat_pb2.Update()
      update.message = message
      update.currentTime = time_utils.current_server_time()
      update.expirationTime = self.expirationTime = update.currentTime + self.sessionLength
      yield update
