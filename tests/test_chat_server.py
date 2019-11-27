from server import chat_server as chat_server_mod
from proto import chat_pb2_grpc, chat_pb2
import grpc
import unittest
import threading
import time

class TestBasicServerFunctionality(unittest.TestCase):
  chat_server = None


  def setUp(self):
    self.chat_server = chat_pb2_grpc.ChatServerStub(TestBasicServerFunctionality.chat_channel)


  @classmethod
  def setUpClass(cls):
    super(TestBasicServerFunctionality, cls).setUpClass()
    chat_server_mod.serve()
    cls.chat_channel = grpc.insecure_channel('localhost:50051')


  @classmethod
  def tearDownClass(cls):
    cls.chat_channel.close()
    chat_server_mod.stop_serving()


  def test_server_gives_out_different_session_ids(self):
    default_thread = chat_pb2.Thread()
    connectionResponse1 = self.chat_server.Connect(default_thread)
    connectionResponse2 = self.chat_server.Connect(default_thread)
    self.assertNotEqual(connectionResponse1.session.uuid.hex, connectionResponse2.session.uuid.hex)
    self.assertNotEqual("00000000000000000000000000000000", connectionResponse1.session.uuid.hex)

  def test_receive_own_messages(self):
    default_thread = chat_pb2.Thread()
    connectionResponse = self.chat_server.Connect(default_thread)
    connectionResponse = self.chat_server.Connect(default_thread)
    receive_response = self.chat_server.ReceiveUpdates(connectionResponse.session)
    sentMessage = chat_pb2.SentMessage()
    sentMessage.contents = "Test123"
    sentMessage.timestamp.timestamp = int(round(time.time() * 1000 * 1000))
    sentMessage.acknowledgement.numMessagesSent = 1
    sentMessage.acknowledgement.session.uuid.hex = connectionResponse.session.uuid.hex
    sentMessage.acknowledgement.session.thread.uuid.hex = connectionResponse.session.thread.uuid.hex
    self.chat_server.SendMessage(sentMessage)
    self.assertIsNotNone(receive_response.next())
    receive_response.close()



if __name__ == '__main__':
  unittest.main()