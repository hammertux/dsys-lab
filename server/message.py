import uuid
from proto import chat_pb2
import threading
class Message:
  def __init__(self, sentMessage):
    self.thread = sentMessage.acknowledgement.session.thread
    self.contents = sentMessage.contents
    self.uuid = uuid.uuid4()
    self.initialized_event = threading.Event()

  def to_received_message(self):
    self.initialized_event.wait()
    received_message = chat_pb2.ReceivedMessage()
    received_message.thread = self.thread
    received_message.contents = self.contents
    received_message.uuid.hex = self.uuid.hex
    received_message.serverTime.timestamp = self.server_time
    return received_message
