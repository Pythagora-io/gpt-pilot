from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest

from core.config import LLMConfig
from core.llm.convo import Convo
from core.llm.openai_client import OpenAIClient


async def mock_response_generator(*content):
    for item in content:
        chunk = MagicMock()
        chunk.choices = [MagicMock(delta=MagicMock(content=item))]
        yield chunk


@pytest.mark.asyncio
@patch("core.llm.openai_client.AsyncOpenAI")
async def test_openai_calls_gpt(mock_AsyncOpenAI):
    cfg = LLMConfig(model="gpt-4-turbo")
    convo = Convo("system hello").user("user hello")

    stream = AsyncMock(return_value=mock_response_generator("hello", None, "world"))
    mock_AsyncOpenAI.return_value.chat.completions.create = stream

    llm = OpenAIClient(cfg)
    response, req_log = await llm(convo, json_mode=True)
    assert response == "helloworld"

    assert req_log.model == cfg.model
    assert req_log.provider == cfg.provider
    assert req_log.temperature == cfg.temperature
    assert req_log.response == response
    assert req_log.status == "success"

    stream.assert_awaited_once_with(
        model="gpt-4-turbo",
        messages=[
            {"role": "system", "content": "system hello"},
            {"role": "user", "content": "user hello"},
        ],
        temperature=0.5,
        stream=True,
        stream_options={"include_usage": True},
        response_format={"type": "json_object"},
    )


@pytest.mark.asyncio
@patch("core.llm.openai_client.AsyncOpenAI")
async def test_openai_stream_handler(mock_AsyncOpenAI):
    cfg = LLMConfig(model="gpt-4-turbo")
    convo = Convo("system hello").user("user hello")

    stream_handler = AsyncMock()

    stream = AsyncMock(return_value=mock_response_generator("hello", None, "world"))
    mock_AsyncOpenAI.return_value.chat.completions.create = stream

    llm = OpenAIClient(cfg, stream_handler=stream_handler)
    await llm(convo)

    stream_handler.assert_has_awaits([call("hello"), call("world")])


@pytest.mark.asyncio
@patch("core.llm.openai_client.AsyncOpenAI")
async def test_openai_parser_with_retries(mock_AsyncOpenAI):
    cfg = LLMConfig(model="gpt-4-turbo")
    convo = Convo("system").user("user")

    parser = MagicMock()
    parser.side_effect = [ValueError("Try again"), "world"]

    stream = AsyncMock(
        side_effect=[
            mock_response_generator("hello"),
            mock_response_generator("world"),
        ]
    )
    mock_AsyncOpenAI.return_value.chat.completions.create = stream

    llm = OpenAIClient(cfg)
    response, req_log = await llm(convo, parser=parser)

    assert response == "world"
    assert stream.await_count == 2
    assert req_log.status == "success"

    assert req_log.messages == [
        {"role": "system", "content": "system"},
        {"role": "user", "content": "user"},
        {"role": "assistant", "content": "hello"},
        {
            "role": "user",
            "content": "Error parsing response: Try again. Please output your response EXACTLY as requested.",
        },
    ]


@pytest.mark.asyncio
@patch("core.llm.openai_client.AsyncOpenAI")
async def test_openai_parser_fails(mock_AsyncOpenAI):
    cfg = LLMConfig(model="gpt-4-turbo")
    convo = Convo("system").user("user")

    parser = MagicMock()
    parser.side_effect = [ValueError("Try again")]

    stream = AsyncMock(return_value=mock_response_generator("hello"))
    mock_AsyncOpenAI.return_value.chat.completions.create = stream

    llm = OpenAIClient(cfg)
    response, req_log = await llm(convo, parser=parser, max_retries=1)

    assert response is None
    assert req_log.status == "error"
