import chat_pb2_grpc # Contains the code necessary for creating the GRPC server and instantiating the service
import chat_pb2 # Contains the code necessary for constructing messages
import session # Keeps track of which clients are connected
import uuid
import time_utils
import message as message_mod
import queue

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
    return self.threads[session.thread.uuid.hex].ReceiveUpdates(session.uuid)
  
  def Acknowlegde(self, acknowledgement):
    self.threads[acknowledgement.session.thread.uuid.hex].Acknowlegde(acknowledgement)
    server_time = chat_pb2.ServerTime()
    server_time.timestamp = time_utils.current_server_time()
    return server_time
  
  def SendMessage(self, sentMessage):
    thread_uuid = string_to_uuid_or_default(thread.uuid.hex, self.default_uuid)
    return self.get_or_create_thread(thread_uuid).SendMessage(sentMessage)
  
  def SendMessages(self, sentMessages):
    for sentMessage in sentMessages:
      yield self.SendMessage(sentMessage)
  
  def start_running(self):
    thread.start_new_thread(self.__broadcast_messages) # Should I add self as an argument here or not?

class ThreadServicer:
  def __init__(self, uuid):
    self.session_store = session.SessionStore()
    self.uuid = uuid
    self.expirationTime = time_utils.current_server_time()
    self.sessionLength = 10*1000*1000 # session length in microseconds
    self.num_updates_sent = 0
    self.num_updates_acknowledged = 0
    self.broadcast_queue = queue.Queue()
    self.max_wait_in_send_message_in_seconds = 1

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
      update.currentTime.timestamp = time_utils.current_server_time()
      update.expirationTime.timestamp = self.expirationTime = update.currentTime + self.sessionLength
      self.num_updates_sent += 1
      yield update

  def Acknowlegde(self, acknowledgement):
    self.num_updates_acknowledged += 1

  def is_session_expired(self):
    return time_utils.current_server_time() > self.expirationTime

  def SendMessage(self):
    message = message_mod.Message(sentMessage)
    try:
      self.broadcast_queue.put(message, True, self.max_wait_in_send_message_in_seconds)
      message.server_time = time_utils.current_server_time()
      message.initialized_event.set()
      timestamp = message.server_time
    except queue.Full:
      status_code = chat_pb2.MessageStatus.StatusCode.NUMERICAL_ERROR
    message_status = chat_pb2.MessageStatus()
    message_status.statusCode = status_code
    if timestamp:
      message_status.timestamp = timestamp
    else:
      message_status.timestamp = time_utils.current_server_time()
    return message_status

  def __broadcast_messages(self):
    while True:
      message = self.broadcast_queue.get()
      received_message = message.to_received_message()
      for session in self.session_store.sessions.values():
        session.messageQueue.put(received_message)
