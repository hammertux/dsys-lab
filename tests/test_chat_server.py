from server import chat_server as chat_server_mod
from proto import chat_pb2
import unittest
import time
from server.thread_configuration import ThreadConfiguration, ThreadConfigurationPolicy
from pprint import pprint

class TestBasicServerFunctionality(unittest.TestCase):
  chat_server = None

  def setUp(self):
    self.thread_configuration = ThreadConfiguration(2, 1, 0.1)
    self.thread_configuration_policy = ThreadConfigurationPolicy(self.thread_configuration)
    self.servicer = chat_server_mod.ChatServicer(self.thread_configuration_policy)
    self.servicer.add_default_thread(self.thread_configuration_policy)
    self.connectionRequest = chat_pb2.ConnectionRequest(name="TestName")

  def test_server_gives_out_different_session_ids(self):
    connectionResponse1 = self.servicer.Connect(self.connectionRequest, None)
    connectionResponse2 = self.servicer.Connect(self.connectionRequest, None)
    self.assertNotEqual(connectionResponse1.session.uuid.hex, connectionResponse2.session.uuid.hex)
    self.assertNotEqual("00000000000000000000000000000000", connectionResponse1.session.uuid.hex)
    self.assertEqual("00000000000000000000000000000000", connectionResponse1.session.thread.uuid.hex)
    self.assertEqual("00000000000000000000000000000000", connectionResponse2.session.thread.uuid.hex)

  def test_receive_own_messages(self):
    connectionResponse = self.servicer.Connect(self.connectionRequest, None)
    connectionResponse = self.servicer.Connect(self.connectionRequest, None)
    receive_response = self.servicer.ReceiveUpdates(connectionResponse.session, None)
    sentMessage = chat_pb2.SentMessage()
    sentMessage.contents = "Test123"
    sentMessage.timestamp.timestamp = int(round(time.time() * 1000 * 1000))
    sentMessage.acknowledgement.numMessagesSent = 1
    sentMessage.acknowledgement.session.uuid.hex = connectionResponse.session.uuid.hex
    sentMessage.acknowledgement.session.thread.uuid.hex = connectionResponse.session.thread.uuid.hex
    message_status = self.servicer.SendMessage(sentMessage, None)
    self.assertEqual(0, message_status.statusCode)
    received_update = next(receive_response)
    while len(received_update.message) == 0:
      received_update = next(receive_response)
    self.assertEqual(sentMessage.contents, received_update.message[0].contents)
    self.assertEqual("TestName", received_update.message[0].sender)
    self.assertIsNotNone(self.servicer.Acknowlegde(chat_pb2.Acknowledgement(session=connectionResponse.session), None).timestamp)

  def test_numerical_error(self):
    self.servicer = chat_server_mod.ChatServicer(ThreadConfigurationPolicy(ThreadConfiguration(10, 10000, 1)))
    self.servicer.add_default_thread(ThreadConfigurationPolicy(ThreadConfiguration(10, 10000, 1)))
    timestamp = int(round(time.time() * 1000 * 1000))
    connectionResponse = self.servicer.Connect(self.connectionRequest, None)
    connectionResponse = self.servicer.Connect(self.connectionRequest, None)
    receive_response = self.servicer.ReceiveUpdates(connectionResponse.session, None)
    sentMessage = chat_pb2.SentMessage()
    sentMessage.contents = "Test123"
    sentMessage.timestamp.timestamp = timestamp
    sentMessage.acknowledgement.session.uuid.hex = connectionResponse.session.uuid.hex
    sentMessage.acknowledgement.session.thread.uuid.hex = connectionResponse.session.thread.uuid.hex
    for i in range(0,11):
      sentMessage.acknowledgement.numMessagesSent = i
      message_status = self.servicer.SendMessage(sentMessage, None)
      if i == 10:
        self.assertEqual(chat_pb2.MessageStatusCode.NUMERICAL_ERROR, message_status.statusCode)
        break
      self.assertEqual(chat_pb2.MessageStatusCode.OK, message_status.statusCode)
      received_update = next(receive_response)
      while len(received_update.message) == 0:
        received_update = next(receive_response)
      self.assertIsNotNone(self.servicer.Acknowlegde(chat_pb2.Acknowledgement(session=connectionResponse.session, numMessagesReceived = i), None).timestamp)
  
  def test_numerical_error_recovery(self):
    self.servicer = chat_server_mod.ChatServicer(ThreadConfigurationPolicy(ThreadConfiguration(10, 10000, 0.1)))
    self.servicer.add_default_thread(ThreadConfigurationPolicy(ThreadConfiguration(10, 10000, 0.1)))
    connectionResponse = self.servicer.Connect(self.connectionRequest, None)
    connectionResponse = self.servicer.Connect(self.connectionRequest, None)
    receive_response = self.servicer.ReceiveUpdates(connectionResponse.session, None)
    sentMessage = chat_pb2.SentMessage()
    sentMessage.contents = "Test123"
    sentMessage.acknowledgement.session.uuid.hex = connectionResponse.session.uuid.hex
    sentMessage.acknowledgement.session.thread.uuid.hex = connectionResponse.session.thread.uuid.hex
    for i in range(0,11):
      if i == 10:
        time.sleep(0.1)
      sentMessage.acknowledgement.numMessagesSent = i
      sentMessage.timestamp.timestamp = int(round(time.time() * 1000 * 1000))
      message_status = self.servicer.SendMessage(sentMessage, None)
      self.assertEqual(chat_pb2.MessageStatusCode.OK, message_status.statusCode)
      received_update = next(receive_response)
      while len(received_update.message) == 0:
        received_update = next(receive_response)
      self.assertIsNotNone(self.servicer.Acknowlegde(chat_pb2.Acknowledgement(session=connectionResponse.session, numMessagesReceived = i), None).timestamp)

  def test_staleness(self):
    max_staleness = 0.1
    self.servicer = chat_server_mod.ChatServicer(ThreadConfigurationPolicy(ThreadConfiguration(10, 10000, max_staleness)))
    self.servicer.add_default_thread(ThreadConfigurationPolicy(ThreadConfiguration(10, 10000, max_staleness)))
    connectionResponse = self.servicer.Connect(self.connectionRequest, None)
    connectionResponse = self.servicer.Connect(self.connectionRequest, None)
    receive_response = self.servicer.ReceiveUpdates(connectionResponse.session, None)
    sentMessage = chat_pb2.SentMessage()
    sentMessage.contents = "Test123"
    sentMessage.timestamp.timestamp = int(round((time.time()-max_staleness) * 1000 * 1000))
    sentMessage.acknowledgement.session.uuid.hex = connectionResponse.session.uuid.hex
    sentMessage.acknowledgement.session.thread.uuid.hex = connectionResponse.session.thread.uuid.hex
    message_status = self.servicer.SendMessage(sentMessage, None)
    self.assertEqual(chat_pb2.MessageStatusCode.STALENESS, message_status.statusCode)
  
  def test_order_error(self):
    self.servicer = chat_server_mod.ChatServicer(ThreadConfigurationPolicy(ThreadConfiguration(10000, 10, 0.1)))
    self.servicer.add_default_thread(ThreadConfigurationPolicy(ThreadConfiguration(10000, 10, 0.1)))
    connectionResponse = self.servicer.Connect(self.connectionRequest, None)
    connectionResponse = self.servicer.Connect(self.connectionRequest, None)
    receive_response = self.servicer.ReceiveUpdates(connectionResponse.session, None)
    sentMessage = chat_pb2.SentMessage()
    sentMessage.contents = "Test123"
    sentMessage.timestamp.timestamp = int(round(time.time() * 1000 * 1000))
    sentMessage.acknowledgement.session.uuid.hex = connectionResponse.session.uuid.hex
    sentMessage.acknowledgement.session.thread.uuid.hex = connectionResponse.session.thread.uuid.hex
    for i in range(0,11):
      message_status = self.servicer.SendMessage(sentMessage, None)
      if i == 10:
        self.assertEqual(chat_pb2.MessageStatusCode.ORDER_ERROR, message_status.statusCode)
        break
      self.assertEqual(chat_pb2.MessageStatusCode.OK, message_status.statusCode)
      received_update = next(receive_response)
      while len(received_update.message) == 0:
        received_update = next(receive_response)
      self.assertIsNotNone(self.servicer.Acknowlegde(chat_pb2.Acknowledgement(session=connectionResponse.session, numMessagesReceived = i), None).timestamp)
  
  def test_auto_refresh(self):
    self.servicer = chat_server_mod.ChatServicer(ThreadConfigurationPolicy(ThreadConfiguration(10000, 10, 0.1)))
    self.servicer.add_default_thread(ThreadConfigurationPolicy(ThreadConfiguration(10000, 10, 0.1)))
    connectionResponse = self.servicer.Connect(self.connectionRequest, None)
    connectionResponse = self.servicer.Connect(self.connectionRequest, None)
    receive_response = self.servicer.ReceiveUpdates(connectionResponse.session, None)
    for i in range(0,2):
      received_update = next(receive_response)
      self.assertEqual(0, len(received_update.message))