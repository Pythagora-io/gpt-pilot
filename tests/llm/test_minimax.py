from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest

from core.config import LLMConfig, LLMProvider
from core.llm.base import APIError
from core.llm.convo import Convo
from core.llm.minimax_client import MiniMaxClient
from core.state.state_manager import StateManager


async def mock_response_generator(*content):
    for item in content:
        chunk = MagicMock()
        chunk.choices = [MagicMock(delta=MagicMock(content=item))]
        chunk.usage = None
        yield chunk


@pytest.mark.asyncio
@patch("core.cli.helpers.StateManager")
@patch("core.llm.minimax_client.AsyncOpenAI")
async def test_minimax_calls_model(mock_AsyncOpenAI, mock_state_manager):
    cfg = LLMConfig(provider=LLMProvider.MINIMAX, model="MiniMax-M2.5", temperature=0.5)
    convo = Convo("system hello").user("user hello")

    stream = AsyncMock(return_value=mock_response_generator("hello", None, "world"))

    mock_chat = AsyncMock()
    mock_completions = AsyncMock()
    mock_completions.create = stream
    mock_chat.completions = mock_completions

    mock_client = AsyncMock()
    mock_client.chat = mock_chat
    mock_AsyncOpenAI.return_value = mock_client

    sm = StateManager(mock_state_manager)
    llm = MiniMaxClient(cfg, state_manager=sm)
    response, req_log = await llm(convo)
    assert response == "helloworld"

    assert req_log.model == "MiniMax-M2.5"
    assert req_log.provider == LLMProvider.MINIMAX
    assert req_log.temperature == 0.5
    assert req_log.response == response
    assert req_log.status == "success"

    stream.assert_awaited_once_with(
        model="MiniMax-M2.5",
        messages=[
            {"role": "system", "content": "system hello"},
            {"role": "user", "content": "user hello"},
        ],
        temperature=0.5,
        stream=True,
    )


@pytest.mark.asyncio
@patch("core.cli.helpers.StateManager")
@patch("core.llm.minimax_client.AsyncOpenAI")
async def test_minimax_temperature_clamping(mock_AsyncOpenAI, mock_state_manager):
    """Test that temperature=0 is clamped to MINIMAX_MIN_TEMPERATURE (0.01)."""
    cfg = LLMConfig(provider=LLMProvider.MINIMAX, model="MiniMax-M2.5", temperature=0.0)
    convo = Convo("system").user("user")

    stream = AsyncMock(return_value=mock_response_generator("ok"))

    mock_chat = AsyncMock()
    mock_completions = AsyncMock()
    mock_completions.create = stream
    mock_chat.completions = mock_completions

    mock_client = AsyncMock()
    mock_client.chat = mock_chat
    mock_AsyncOpenAI.return_value = mock_client

    sm = StateManager(mock_state_manager)
    llm = MiniMaxClient(cfg, state_manager=sm)
    await llm(convo)

    # Verify temperature was clamped to 0.01 instead of 0.0
    stream.assert_awaited_once()
    call_kwargs = stream.call_args[1] if stream.call_args[1] else {}
    if not call_kwargs:
        call_kwargs = dict(zip(["model", "messages", "temperature", "stream"], stream.call_args[0]))
    assert call_kwargs.get("temperature", stream.call_args.kwargs.get("temperature")) == 0.01


@pytest.mark.asyncio
@patch("core.cli.helpers.StateManager")
@patch("core.llm.minimax_client.AsyncOpenAI")
async def test_minimax_no_json_mode(mock_AsyncOpenAI, mock_state_manager):
    """Test that json_mode=True does NOT add response_format (MiniMax doesn't support it)."""
    cfg = LLMConfig(provider=LLMProvider.MINIMAX, model="MiniMax-M2.5", temperature=0.5)
    convo = Convo("system").user("user")

    stream = AsyncMock(return_value=mock_response_generator("ok"))

    mock_chat = AsyncMock()
    mock_completions = AsyncMock()
    mock_completions.create = stream
    mock_chat.completions = mock_completions

    mock_client = AsyncMock()
    mock_client.chat = mock_chat
    mock_AsyncOpenAI.return_value = mock_client

    sm = StateManager(mock_state_manager)
    llm = MiniMaxClient(cfg, state_manager=sm)
    await llm(convo, json_mode=True)

    # Verify response_format was NOT included in the call
    call_kwargs = stream.call_args.kwargs
    assert "response_format" not in call_kwargs


@pytest.mark.asyncio
@patch("core.cli.helpers.StateManager")
@patch("core.llm.minimax_client.AsyncOpenAI")
async def test_minimax_stream_handler(mock_AsyncOpenAI, mock_state_manager):
    cfg = LLMConfig(provider=LLMProvider.MINIMAX, model="MiniMax-M2.5", temperature=0.5)
    convo = Convo("system hello").user("user hello")

    stream_handler = AsyncMock()

    stream = AsyncMock(return_value=mock_response_generator("hello", None, "world"))

    mock_chat = AsyncMock()
    mock_completions = AsyncMock()
    mock_completions.create = stream
    mock_chat.completions = mock_completions

    mock_client = AsyncMock()
    mock_client.chat = mock_chat
    mock_AsyncOpenAI.return_value = mock_client

    sm = StateManager(mock_state_manager)
    llm = MiniMaxClient(cfg, stream_handler=stream_handler, state_manager=sm)
    await llm(convo)

    stream_handler.assert_has_awaits([call("hello"), call("world")])


@pytest.mark.asyncio
@patch("core.cli.helpers.StateManager")
@patch("core.llm.minimax_client.AsyncOpenAI")
async def test_minimax_default_base_url(mock_AsyncOpenAI, mock_state_manager):
    """Test that the default base URL is set to MiniMax API endpoint."""
    cfg = LLMConfig(provider=LLMProvider.MINIMAX, model="MiniMax-M2.5", temperature=0.5)

    sm = StateManager(mock_state_manager)
    MiniMaxClient(cfg, state_manager=sm)

    mock_AsyncOpenAI.assert_called_once()
    call_kwargs = mock_AsyncOpenAI.call_args.kwargs
    assert call_kwargs["base_url"] == "https://api.minimax.io/v1"


@pytest.mark.asyncio
@patch("core.cli.helpers.StateManager")
@patch("core.llm.minimax_client.AsyncOpenAI")
async def test_minimax_custom_base_url(mock_AsyncOpenAI, mock_state_manager):
    """Test that a custom base URL overrides the default."""
    cfg = LLMConfig(
        provider=LLMProvider.MINIMAX,
        model="MiniMax-M2.5",
        temperature=0.5,
        base_url="https://api.minimaxi.com/v1",
    )

    sm = StateManager(mock_state_manager)
    MiniMaxClient(cfg, state_manager=sm)

    mock_AsyncOpenAI.assert_called_once()
    call_kwargs = mock_AsyncOpenAI.call_args.kwargs
    assert call_kwargs["base_url"] == "https://api.minimaxi.com/v1"


@pytest.mark.parametrize(
    ("remaining_tokens", "reset_tokens", "reset_requests", "expected"),
    [
        (0, "1h1m1s", "", 3661),
        (0, "1m", "", 60),
        (1, "", "1h1m1s", 3661),
    ],
)
@patch("core.cli.helpers.StateManager")
@patch("core.llm.minimax_client.AsyncOpenAI")
def test_minimax_rate_limit_parser(
    mock_AsyncOpenAI, mock_state_manager, remaining_tokens, reset_tokens, reset_requests, expected
):
    headers = {
        "x-ratelimit-remaining-tokens": remaining_tokens,
        "x-ratelimit-reset-tokens": reset_tokens,
        "x-ratelimit-reset-requests": reset_requests,
    }
    err = MagicMock(response=MagicMock(headers=headers))

    sm = StateManager(mock_state_manager)
    llm = MiniMaxClient(LLMConfig(provider=LLMProvider.MINIMAX, model="MiniMax-M2.5"), state_manager=sm)
    assert int(llm.rate_limit_sleep(err).total_seconds()) == expected


@patch("core.cli.helpers.StateManager")
@patch("core.llm.minimax_client.AsyncOpenAI")
def test_minimax_rate_limit_retry_after(mock_AsyncOpenAI, mock_state_manager):
    """Test rate limiting with retry-after header."""
    headers = {"retry-after": "30"}
    err = MagicMock(response=MagicMock(headers=headers))

    sm = StateManager(mock_state_manager)
    llm = MiniMaxClient(LLMConfig(provider=LLMProvider.MINIMAX, model="MiniMax-M2.5"), state_manager=sm)
    assert int(llm.rate_limit_sleep(err).total_seconds()) == 30
