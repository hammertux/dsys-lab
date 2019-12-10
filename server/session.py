from proto import chat_pb2 # Contains the code necessary for constructing messages
import uuid # Contains code for universally unique identifiers
import queue
import threading
from . import time_utils
from . import message as message_mod
from .acknowledgement_tracker import AcknowledgementTracker, ProxyAcknowledgeable
from .queue_generator import StoppableQueueGenerator
import time

class SessionStore:
  def __init__(self):
    self.dict = {}

  def create(self, thread_servicer, name):
    session = Session(thread_servicer, name)
    return session
  
  def add(self, session):
    self.dict[session.uuid] = session
  
  def retrieve(self, uuid):
    return self.dict[uuid]

  def retrieve_by_hex(self, hex):
    return self.dict[uuid.UUID(hex=hex)]

class SessionMessage:
  def __init__(self, message, acknowledgeable):
    self.message = message
    self.acknowledgeable = ProxyAcknowledgeable(acknowledgeable)

class TimedSession:
  def __init__(self, session_length, refresh_time):
    self.session_length = session_length
    self.refresh_time = refresh_time
    self.expiration_time = time_utils.current_server_time()
    self.lock = threading.Lock()
    self.extend()

  def extend(self):
    with self.lock:
      new_expiration_time = time_utils.current_server_time() + self.session_length
      if new_expiration_time < self.expiration_time:
        return
      self.expiration_time = new_expiration_time
      self.timer = threading.Timer(time_utils.to_python_time(self.refresh_time), self._auto_extend)
      self.timer.start()
  
  def _auto_extend(self):
    self.extend()

class Session(AcknowledgementTracker, message_mod.ChatCommittable, TimedSession):
  def __init__(self, thread_servicer, name):
    AcknowledgementTracker.__init__(self)
    # uuid of the session
    self.uuid = uuid.uuid4()
    self.name = name
    self.thread_servicer = thread_servicer
    # queue containing messages that need to be sent to the client
    self.message_queue = queue.Queue()
    self.message_queue_generator = StoppableQueueGenerator(self.message_queue)
    TimedSession.__init__(self, int(thread_servicer.session_length * 1000 * 1000), int(thread_servicer.session_refresh_time * 1000 * 1000))

    # lock used by ReceiveUpdates
    self.__receive_updates_lock = threading.Lock()

    # the last commit number for which the client did not receive updates (one lower than the first for which they will receive an update at some point)
    self.last_commit_number_not_received = None
  
  def update_timed_session_configuration(self, session_length, session_refresh_time):
    self.session_length = session_length * 1000 * 1000
    self.refresh_time = session_refresh_time * 1000 * 1000

  def Acknowledge(self, acknowledgement):
    self.acknowledge_upto(acknowledgement.numMessagesReceived)
  
  def _after_acknowledge(self, count):
    pass
  
  def _auto_extend(self):
    self.message_queue.put(None)

  # Triggers a shutdown of the active thread in this session
  def trigger_shutdown(self):
    self.message_queue_generator.stop()

  def ReceiveUpdates(self):
    # acquire the lock to ensure that only one such connection exists per session at a time
    # the lock is never released
    if not self.__receive_updates_lock.acquire(False):
      return
    
    try:
      for message in self.message_queue_generator.generate(): # blocks until items appear in the queue
        if message is not None:
          # for consistency, we do not return messages before last_commit_number_not_received and all messages after it
          if message.message.commit_number <= self.last_commit_number_not_received:
            message.acknowledgeable.acknowledge()
            message = None

        # postpone the expiration time if possible
        if self._can_extend():
          self.extend()

        # construct an update message
        update = message_mod.Update(self.expiration_time)
        if message is not None:
          update.add_message(message.message)
        print("Sending")

        # write the update to the client
        yield update.to_chat_pb2()
    finally:
      self.__receive_updates_lock.release()
  
  def _can_extend(self):
    return self.message_queue.empty()

  def _on_session_expired(self):
    pass

  def __check_session_expired(self):
    if self.has_session_expired():
      self._on_session_expired()

  def has_session_expired(self):
    return time_utils.current_server_time() > self.expiration_time

  def commit(self):
    self.last_commit_number_not_received = self.thread_servicer.last_commit_number
    self.thread_servicer.session_store.add(self)
