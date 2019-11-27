import uuid
from . import time_utils
from proto import chat_pb2
import threading

class Message:
  """Constructs a new Message based on a SentMessage. For thread safety, all functionality is blocked until complete_initalization is called."""
  def __init__(self, sentMessage, senderName):
    self.thread = sentMessage.acknowledgement.session.thread
    self.contents = sentMessage.contents
    self.uuid = uuid.uuid4()
    self.__initialized_event = threading.Event()
    self.server_time = None
    self.senderName = senderName
  
  """Completes the iniatlization of the message, allowing other threads to use its data"""
  def complete_initalization(self):
    # mark it as initialized (this mechanism is necessary to ensure that the message has a consistent time)
    self.__initialized_event.set()

  def to_received_message(self):
    self.__initialized_event.wait()
    received_message = chat_pb2.ReceivedMessage()
    received_message.thread.uuid.hex = self.thread.uuid.hex
    received_message.contents = self.contents
    received_message.uuid.hex = self.uuid.hex
    received_message.serverTime.timestamp = self.server_time
    received_message.sender = self.senderName
    return received_message


class Update:
  def __init__(self, relativeExpirationTime):
    self.pb2_update = chat_pb2.Update()
    timestamp = time_utils.current_server_time()
    self.pb2_update.currentTime.timestamp = timestamp
    self.pb2_update.expirationTime.timestamp = timestamp + relativeExpirationTime
  
  def add_message(self, message):
    self.pb2_update.message.append(message.to_received_message())
  
  def to_chat_pb2(self):
    return self.pb2_update
