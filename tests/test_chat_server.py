from server import chat_server as chat_server_mod
from proto import chat_pb2
import unittest
import time
from pprint import pprint

class TestBasicServerFunctionality(unittest.TestCase):
  chat_server = None

  def setUp(self):
    self.servicer = chat_server_mod.ChatServicer()

  def test_server_gives_out_different_session_ids(self):
    default_thread = chat_pb2.Thread()
    connectionResponse1 = self.servicer.Connect(default_thread, None)
    connectionResponse2 = self.servicer.Connect(default_thread, None)
    self.assertNotEqual(connectionResponse1.session.uuid.hex, connectionResponse2.session.uuid.hex)
    self.assertNotEqual("00000000000000000000000000000000", connectionResponse1.session.uuid.hex)
    self.assertEqual("00000000000000000000000000000000", connectionResponse1.session.thread.uuid.hex)
    self.assertEqual("00000000000000000000000000000000", connectionResponse2.session.thread.uuid.hex)

  def test_receive_own_messages(self):
    default_thread = chat_pb2.Thread()
    connectionResponse = self.servicer.Connect(default_thread, None)
    connectionResponse = self.servicer.Connect(default_thread, None)
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
    self.assertEqual(sentMessage.contents, received_update.message[0].contents)
    self.assertIsNotNone(self.servicer.Acknowlegde(chat_pb2.Acknowledgement(session=connectionResponse.session), None).timestamp)
