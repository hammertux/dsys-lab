from proto import chat_pb2 # Contains the code necessary for constructing messages
import uuid # Contains code for universally unique identifiers
import queue
import threading
from . import time_utils

class SessionStore:
  def __init__(self):
    self.sessions = {}

  def create(self):
    session = Session()
    self.sessions[session.uuid] = session
    return session
  
  def retrieve(self, uuid):
    return self.sessions[uuid]

class Session:
  def __init__(self):
    self.uuid = uuid.uuid4()
    self.messageQueue = queue.Queue()
    self.numUpdatesSent = 0
    self.numMessagesSent = 0
    self.numUpdatesAcknowledged = 0
    self.numMessagesAcknowledged = 0
    self.expirationTime = time_utils.current_server_time()
    self.sessionLength = 10*1000*1000 # session length in microseconds
    self.__acknowledgementLock = threading.Lock()
  
  def Acknowledge(self, acknowledgement):
    # First check if locking is necessary
    if acknowledgement.numUpdatesReceived > self.numUpdatesAcknowledged or acknowledgement.numMessagesReceived > self.numMessagesAcknowledged:
      self.__acknowledgementLock.acquire()
      # take the maximum number of updates acknowledged because the acknowledgements are not guaranteed to arrive in the correct order
      self.numUpdatesAcknowledged = max(acknowledgement.numUpdatesReceived, self.numUpdatesAcknowledged)
      self.numMessagesAcknowledged = max(acknowledgement.numMessagesReceived, self.numMessagesAcknowledged)
      self.__acknowledgementLock.release()

  def ReceiveUpdates(self):
    while True:
      message = self.messageQueue.get() # blocks until there are elements in the queue
      update = chat_pb2.Update()
      update.message = message
      update.currentTime.timestamp = time_utils.current_server_time()
      update.expirationTime.timestamp = self.expirationTime = update.currentTime + self.sessionLength
      
      yield update

  def is_session_expired(self):
    return time_utils.current_server_time() > self.expirationTime4