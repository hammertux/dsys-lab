import uuid
from . import time_utils
from proto import chat_pb2
import threading
from . import consistency_requirement
from .consistency_requirement import CommitTooLate
from .acknowledgement_tracker import Acknowledgeable

class ChatCommittable(consistency_requirement.Committable):
  def add_to_update(self, update):
    pass

class Message(ChatCommittable):
  """Constructs a new Message based on a SentMessage."""
  def __init__(self, sentMessage, commit_deadline, on_commit, sender_session, commit_number_generator):
    self.thread = sentMessage.acknowledgement.session.thread
    self.contents = sentMessage.contents
    self.uuid = uuid.uuid4()
    self.__initialized_event = threading.Event()
    self.initalized = False
    self.sent_time = sentMessage.timestamp.timestamp
    self.commit_deadline = commit_deadline
    self.commit_time = None
    self.commit_number = None
    self.on_commit = on_commit
    self.commit_number_generator = commit_number_generator
    self.sender_name = sender_session.name
    if sender_session.last_commit_number_not_received is not None:
      self.last_commit_number_received_by_sender = sentMessage.acknowledgement.numMessagesReceived + sender_session.last_commit_number_not_received

  def to_received_message(self):
    received_message = chat_pb2.ReceivedMessage()
    received_message.thread.uuid.hex = self.thread.uuid.hex
    received_message.contents = self.contents
    received_message.uuid.hex = self.uuid.hex
    received_message.serverTime.timestamp = self.commit_time
    received_message.sender = self.sender_name
    return received_message

  def add_to_update(self, update):
    update.pb2_update.message.append(self.to_received_message())

  # Returns how much time is left before the commit deadline (optimistically)
  def time_left_before_commit_deadline(self):
    return self.commit_deadline - time_utils.current_server_time()

  def commit(self):
    commit_time = time_utils.current_server_time()
    if commit_time > self.commit_deadline:
      raise CommitTooLate(commit_time)
    self.commit_time = commit_time
    self.commit_number = next(self.commit_number_generator)
    self.on_commit(self)

class Update:
  def __init__(self, expiration_time):
    self.pb2_update = chat_pb2.Update()
    timestamp = time_utils.current_server_time()
    self.pb2_update.currentTime.timestamp = timestamp
    self.pb2_update.expirationTime.timestamp = expiration_time
  
  def add_message(self, message):
    message.add_to_update(self)
  
  def to_chat_pb2(self):
    return self.pb2_update
