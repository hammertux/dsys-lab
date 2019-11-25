import chat_pb2 # Contains the code necessary for constructing messages
import uuid # Contains code for universally unique identifiers
import queue
import object_store

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
