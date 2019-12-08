from threading import Condition, Lock
from time import time
from . import time_utils
from proto import chat_pb2
class Committable:
  def commit(self):
    pass

# Indicates that the sent message could not be committed in time
class CommitTooLate(Exception):
  def __init__(self, attempted_commit_time):
    self.attempted_commit_time = attempted_commit_time
  def to_message_status(self):
    return chat_pb2.MessageStatus(
      statusCode = chat_pb2.MessageStatusCode.STALENESS,
      messageTime = chat_pb2.ServerTime(timestamp = self.attempted_commit_time)
    )

class ConsistencyRequirement:
  # a timeout of none indicates that the function should wait indefinitely
  def perform_commit(self, write, timeout, commit_function):
    pass
  def commit(self, committable, timeout = None):
    self.perform_commit(committable, timeout, lambda new_committable : new_committable.commit())

class CompositeRequirement(ConsistencyRequirement):
  def __init__(self, firstReq, secondReq):
    self.firstReq = firstReq
    self.secondReq = secondReq
  
  def perform_commit(self, write, timeout, commit_function):
    if timeout is not None and timeout < 0:
      raise CommitTooLate(time_utils.current_server_time())
    if timeout is not None:
      end = time() + timeout
    self.firstReq.perform_commit(write, timeout, lambda new_write : 
      self.secondReq.perform_commit(new_write, (end - time()) if timeout is not None else None, commit_function)
    )

class OrderEnforcer(ConsistencyRequirement):
  def __init__(self):
    self.lock = Lock()
  
  def perform_commit(self, write, timeout, commit_function):
    with self.lock:
      commit_function(write)
