import asyncio
import json
import sys

import pytest

from core.config import LocalIPCConfig
from core.ui.base import AgentSource, UIClosedError
from core.ui.ipc_client import IPCClientUI

if sys.platform == "win32":
    pytest.skip(
        "Skipping IPC Client tests on Windows due to mock server timeouts",
        allow_module_level=True,
    )


class IPCServer:
    """
    Fake IPC server mocking the VSCode extension host.
    """

    def __init__(self, responses: list[dict]):
        """
        Set up the IPC server with a list of responses.
        The server will pop responses from the list in order.
        The number of responses must be equal to the number of calls.
        made. If a response is not needed for a particular call, the
        response can be None, otherwise it should be a dict.

        (Note that the client always sends one extra EXIT message).

        :param responses: List of responses to send to the client.
        """
        self.responses = responses
        self.messages = []
        self.server = None

    async def handle_connection(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ):
        """
        Connection handler used by asyncio.start_server.
        """

        while len(self.responses):
            data = await reader.read(65536)

            while len(data):
                # VSCode IPC protocol: first 4 bytes are the message length
                data_len = int.from_bytes(data[:4], byteorder="big")
                payload_json = data[4 : 4 + data_len]

                # Record the incoming message
                payload = json.loads(payload_json.decode("utf-8"))
                self.messages.append(payload)

                # Since data can have multiple messages, we need to check
                # if there are any more responses again here.
                response = self.responses.pop(0) if len(self.responses) else None
                if response is not None:
                    writer.write(json.dumps(response).encode("utf-8"))
                    await writer.drain()

                data = data[4 + data_len :]

        writer.close()
        await writer.wait_closed()

    async def __aenter__(self) -> tuple[int, list]:
        self.server = await asyncio.start_server(self.handle_connection, "127.0.0.1", 0)
        port = self.server.sockets[0].getsockname()[1]
        return port, self.messages

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # We want the "async with" block to wait for all the server-side work
        while len(self.responses):
            await asyncio.sleep(0.01)
        self.server.close()
        await self.server.wait_closed()


@pytest.mark.asyncio
async def test_send_message():
    server_responses = [None, None]

    async with IPCServer(server_responses) as (port, messages):
        src = AgentSource("Product Owner", "product-owner")
        ui = IPCClientUI(LocalIPCConfig(port=port))

        connected = await ui.start()
        assert connected is True
        await ui.send_message("Hello from the other side ♫", source=src, project_state_id="123", extra_info="test")
        await ui.stop()

    assert messages == [
        {
            "type": "verbose",
            "content": "Hello from the other side ♫",
            "category": "agent:product-owner",
            "project_state_id": "123",
            "full_screen": False,
            "extra_info": "test",
            "placeholder": None,
        },
        {
            "type": "exit",
            "content": None,
            "category": None,
            "project_state_id": None,
            "full_screen": False,
            "extra_info": None,
            "placeholder": None,
        },
    ]


@pytest.mark.asyncio
async def test_stream():
    server_responses = [None, None, None]

    async with IPCServer(server_responses) as (port, messages):
        src = AgentSource("Product Owner", "product-owner")
        ui = IPCClientUI(LocalIPCConfig(port=port))

        connected = await ui.start()
        assert connected is True

        for word in ["Hello", "world"]:
            await ui.send_stream_chunk(word, source=src, project_state_id="123")
            await asyncio.sleep(0.01)
        await ui.stop()

    assert messages == [
        {
            "type": "stream",
            "content": "Hello",
            "category": "agent:product-owner",
            "project_state_id": "123",
            "full_screen": False,
            "extra_info": None,
            "placeholder": None,
        },
        {
            "type": "stream",
            "content": "world",
            "category": "agent:product-owner",
            "project_state_id": "123",
            "full_screen": False,
            "extra_info": None,
            "placeholder": None,
        },
        {
            "type": "exit",
            "content": None,
            "category": None,
            "project_state_id": None,
            "full_screen": False,
            "extra_info": None,
            "placeholder": None,
        },
    ]


@pytest.mark.asyncio
async def test_server_not_running():
    ui = IPCClientUI(LocalIPCConfig(port=1))
    connected = await ui.start()

    assert connected is False


@pytest.mark.asyncio
async def test_server_closes_connection():
    async with IPCServer([]) as (port, _messages):
        ui = IPCClientUI(LocalIPCConfig(port=port))

        connected = await ui.start()
        assert connected is True

        with pytest.raises(UIClosedError):
            await ui.ask_question("Hello, how are you?")


@pytest.mark.asyncio
async def test_ask_question():
    server_responses = [
        {
            "type": "response",
            "content": "I'm fine, thank you!",
        },
        None,
    ]

    async with IPCServer(server_responses) as (port, _messages):
        ui = IPCClientUI(LocalIPCConfig(port=port))

        await ui.start()
        answer = await ui.ask_question("Hello, how are you?")

        await ui.stop()

    assert answer.cancelled is False
    assert answer.text == "I'm fine, thank you!"


@pytest.mark.asyncio
async def test_ask_question_buttons():
    server_responses = [
        {
            "type": "response",
            # VSC ext. responds with button label
            "content": "Yes, I'm sure",
        },
        None,
    ]

    async with IPCServer(server_responses) as (port, _messages):
        ui = IPCClientUI(LocalIPCConfig(port=port))

        await ui.start()
        answer = await ui.ask_question(
            "Are you sure",
            buttons={
                "yes": "Yes, I'm sure",
                "no": "No, cancel",
            },
        )

        await ui.stop()

    assert answer.cancelled is False
    assert answer.button == "yes"


@pytest.mark.asyncio
async def test_ask_question_buttons_only_with_default():
    server_responses = [
        {
            "type": "response",
            "content": "",
        },
        None,
    ]

    async with IPCServer(server_responses) as (port, _messages):
        ui = IPCClientUI(LocalIPCConfig(port=port))

        await ui.start()
        answer = await ui.ask_question(
            "Are you sure",
            buttons={
                "yes": "Yes, I'm sure",
                "no": "No, cancel",
            },
            buttons_only=True,
            default="no",
        )

        await ui.stop()

    assert answer.cancelled is False
    assert answer.button == "no"


@pytest.mark.asyncio
async def test_handle_garbage_response():
    server_responses = ["", {"incorrect": "payload"}, None]

    async with IPCServer(server_responses) as (port, _messages):
        ui = IPCClientUI(LocalIPCConfig(port=port))

        await ui.start()

        # These two are only because our fake server expect to receive one and then
        # send one messages, and ask_question() should ignore the two
        # incorrectly-formatted responses
        await ui.send_message("fake1")
        await ui.send_message("fake2")

        with pytest.raises(UIClosedError):
            await ui.ask_question("Are you sure")

        await ui.stop()
