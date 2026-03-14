from os import getenv
from unittest.mock import MagicMock

import pytest

from core.config import LLMConfig, LLMProvider
from core.llm.base import APIError
from core.llm.convo import Convo
from core.llm.minimax_client import MiniMaxClient

run_integration_tests = getenv("INTEGRATION_TESTS", "").lower()
if run_integration_tests not in ["true", "yes", "1", "on"]:
    pytest.skip("Skipping integration tests", allow_module_level=True)

if not getenv("MINIMAX_API_KEY"):
    pytest.skip(
        "Skipping MiniMax integration tests: MINIMAX_API_KEY is not set",
        allow_module_level=True,
    )


def _mock_state_manager():
    sm = MagicMock()
    sm.get_access_token = MagicMock(return_value=None)
    return sm


@pytest.mark.asyncio
async def test_incorrect_key():
    cfg = LLMConfig(
        provider=LLMProvider.MINIMAX,
        model="MiniMax-M2.5",
        api_key="invalid-key",
        base_url="https://api.minimax.io/v1",
        temperature=0.5,
    )

    llm = MiniMaxClient(cfg, state_manager=_mock_state_manager())
    convo = Convo("you're a friendly assistant").user("tell me a joke")

    with pytest.raises(APIError):
        await llm(convo)


@pytest.mark.asyncio
async def test_minimax_success():
    cfg = LLMConfig(
        provider=LLMProvider.MINIMAX,
        model="MiniMax-M2.5",
        base_url="https://api.minimax.io/v1",
        temperature=0.5,
    )

    streamed_response = []

    async def stream_handler(content: str):
        if content:
            streamed_response.append(content)

    llm = MiniMaxClient(cfg, state_manager=_mock_state_manager(), stream_handler=stream_handler)
    convo = Convo("you're a friendly assistant").user("tell me a joke")

    response, req_log = await llm(convo)
    assert response == "".join(streamed_response)

    assert req_log.messages == convo.messages
    assert req_log.prompt_tokens > 0
    assert req_log.completion_tokens > 0


@pytest.mark.asyncio
async def test_minimax_highspeed_model():
    cfg = LLMConfig(
        provider=LLMProvider.MINIMAX,
        model="MiniMax-M2.5-highspeed",
        base_url="https://api.minimax.io/v1",
        temperature=0.5,
    )

    llm = MiniMaxClient(cfg, state_manager=_mock_state_manager())
    convo = Convo("you're a friendly assistant").user("say hello")

    response, req_log = await llm(convo)
    assert len(response) > 0
    assert req_log.model == "MiniMax-M2.5-highspeed"
