import asyncio
from django.test import TransactionTestCase
from channels.testing import WebsocketCommunicator
from asgi import application

class RollCommandTests(TransactionTestCase):
    def setUp(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def tearDown(self):
        self.loop.close()
        asyncio.set_event_loop(None)

    def test_roll_command_returns_system_message(self):
        async def init_com():
            return WebsocketCommunicator(application, "/ws/chat/testroom/")

        communicator = self.loop.run_until_complete(init_com())
        connected, _ = self.loop.run_until_complete(communicator.connect())
        self.assertTrue(connected)

        # 第一个消息是欢迎信息
        self.loop.run_until_complete(communicator.receive_json_from())

        self.loop.run_until_complete(communicator.send_json_to({"message": "/roll 6"}))
        response = self.loop.run_until_complete(communicator.receive_json_from())
        self.loop.run_until_complete(communicator.disconnect())

        self.assertEqual(response.get("username"), "系统")
        self.assertIn("掷出了", response.get("message", ""))
