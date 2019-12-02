from proto import chat_pb2 # Contains the code necessary for constructing messages
import uuid # Contains code for universally unique identifiers
import queue
import threading
from . import time_utils
from . import message as message_mod

class SessionStore:
  def __init__(self):
    self.sessions = {}

  def create(self, name):
    session = Session(name)
    self.sessions[session.uuid] = session
    return session
  
  def retrieve(self, uuid):
    return self.sessions[uuid]

  def retrieve_by_hex(self, hex):
    return self.sessions[uuid.UUID(hex=hex)]

class Session:
  def __init__(self, name):
    # uuid of the session
    self.uuid = uuid.uuid4()

    # the display name when sending messages
    self.name = name

    # queue containing messages that need to be sent to the clients
    self.messageQueue = queue.Queue()
    # consistency metrics
    self.numUpdatesSent = 0
    self.numMessagesSent = 0
    self.numUpdatesAcknowledged = 0
    self.numMessagesAcknowledged = 0

    # expiration time of the session
    self.expirationTime = time_utils.current_server_time()

    # length of a session in microseconds
    self.sessionLength = 10*1000*1000 # 10 seconds

    # lock used by the Acknowledge function to avoid concurrency issues
    self.__acknowledgementLock = threading.Lock()

    # indicates to this thread whether it should stop
    self.__should_shutdown = False

    # lock used by ReceiveUpdates
    self.__receiveUpdatesLock = threading.Lock()
  
  def Acknowledge(self, acknowledgement):
    # First check if locking is necessary
    if acknowledgement.numUpdatesReceived > self.numUpdatesAcknowledged or acknowledgement.numMessagesReceived > self.numMessagesAcknowledged:
      # acquire the lock to avoid concurrency issues
      with self.__acknowledgementLock:
        # take the maximum number of updates acknowledged because the acknowledgements are not guaranteed to arrive in the correct order
        self.numUpdatesAcknowledged = max(acknowledgement.numUpdatesReceived, self.numUpdatesAcknowledged)
        self.numMessagesAcknowledged = max(acknowledgement.numMessagesReceived, self.numMessagesAcknowledged)
  
  # Triggers a shutdown of the active thread in this session
  def trigger_shutdown(self):
    self.__should_shutdown = True
    try:
      self.messageQueue.put_nowait(None)
    except:
      # queue is apparently full so no need to add new elements
      pass


  def ReceiveUpdates(self):
    # acquire the lock to ensure that only one such connection exists per session
    # the lock is never released
    if not self.__receiveUpdatesLock.acquire(False):
      return
    
    # for every message in the queue
    while True:
      message = self.messageQueue.get() # blocks until there are elements in the queue

      # A None in the queue indicates to this thread that it should stop
      if self.__should_shutdown:
        break
        
      # construct an update message
      update = message_mod.Update(self.sessionLength)
      update.add_message(message)
      print("Sending")

      self.numUpdatesSent += 1
      self.numMessagesSent += 1

      # send it to the client
      yield update.to_chat_pb2()


  def is_session_expired(self):
    return time_utils.current_server_time() > self.expirationTime