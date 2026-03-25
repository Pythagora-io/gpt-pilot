"""
Tests for rate limit sleep duration handling in BaseLLMClient.

Verifies that the sleep duration is correctly computed using
total_seconds() and clamped to a reasonable range (1s to 3600s).
"""

import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import openai
import pytest

from core.config import LLMConfig
from core.llm.convo import Convo
from core.llm.openai_client import OpenAIClient
from core.state.state_manager import StateManager


async def mock_response_generator(*content):
    for item in content:
        chunk = MagicMock()
        chunk.choices = [MagicMock(delta=MagicMock(content=item))]
        yield chunk


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("sleep_timedelta", "expected_sleep"),
    [
        # Normal case: 11 seconds from rate limit header
        (datetime.timedelta(seconds=11), 11),
        # Large value from OpenAI: 2 hours should be capped at 3600
        (datetime.timedelta(seconds=7200), 3600),
        # Anthropic daily rate limit: 24h becomes timedelta(days=1),
        # .seconds would be 0 but total_seconds() is 86400, capped to 3600
        (datetime.timedelta(days=1), 3600),
        # Negative timedelta (clock drift): .seconds would be 86395
        # but total_seconds() is -5, clamped to minimum of 1
        (datetime.timedelta(seconds=-5), 1),
        # Small positive timedelta
        (datetime.timedelta(seconds=1), 1),
        # Edge case: exactly 1 hour
        (datetime.timedelta(hours=1), 3600),
        # Fractional seconds (e.g. 11.276s from OpenAI message)
        (datetime.timedelta(seconds=11.276), 11),
    ],
)
@patch("core.cli.helpers.StateManager")
@patch("core.llm.openai_client.AsyncOpenAI")
async def test_rate_limit_sleep_duration_is_clamped(
    mock_AsyncOpenAI, mock_state_manager, sleep_timedelta, expected_sleep
):
    """
    Test that the rate limit sleep duration correctly uses total_seconds()
    and is clamped between 1 and 3600 seconds.
    """
    cfg = LLMConfig(model="gpt-4-turbo")
    convo = Convo("system hello").user("user hello")

    sm = StateManager(mock_state_manager)

    # Set up mock chain
    mock_chat = AsyncMock()
    mock_completions = AsyncMock()
    mock_chat.completions = mock_completions
    mock_client = AsyncMock()
    mock_client.chat = mock_chat
    mock_AsyncOpenAI.return_value = mock_client

    llm = OpenAIClient(cfg, state_manager=sm)

    # Mock rate_limit_sleep to return the test timedelta
    llm.rate_limit_sleep = MagicMock(return_value=sleep_timedelta)

    # First call raises RateLimitError, second call succeeds
    mock_response = MagicMock()
    mock_response.headers = {}
    mock_response.json.return_value = {"error": {"message": "rate limited"}}

    rate_limit_err = openai.RateLimitError(
        message="Rate limit exceeded",
        response=mock_response,
        body={"error": {"message": "rate limited"}},
    )

    llm._make_request = AsyncMock(
        side_effect=[
            rate_limit_err,
            ("success", 10, 5),
        ]
    )

    with patch("core.llm.base.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        response, req_log = await llm(convo)

        mock_sleep.assert_awaited_once_with(expected_sleep)
        assert response == "success"


@pytest.mark.asyncio
@patch("core.cli.helpers.StateManager")
@patch("core.llm.openai_client.AsyncOpenAI")
async def test_rate_limit_none_raises_api_error(mock_AsyncOpenAI, mock_state_manager):
    """
    Test that when rate_limit_sleep returns None (e.g. insufficient funds),
    the error is raised instead of retrying.
    """
    cfg = LLMConfig(model="gpt-4-turbo")
    convo = Convo("system hello").user("user hello")

    sm = StateManager(mock_state_manager)

    mock_chat = AsyncMock()
    mock_completions = AsyncMock()
    mock_chat.completions = mock_completions
    mock_client = AsyncMock()
    mock_client.chat = mock_chat
    mock_AsyncOpenAI.return_value = mock_client

    llm = OpenAIClient(cfg, state_manager=sm)

    # rate_limit_sleep returns None = do not retry
    llm.rate_limit_sleep = MagicMock(return_value=None)

    mock_response = MagicMock()
    mock_response.headers = {}
    mock_response.json.return_value = {"error": {"message": "Insufficient funds"}}

    rate_limit_err = openai.RateLimitError(
        message="Rate limit exceeded",
        response=mock_response,
        body={"error": {"message": "Insufficient funds"}},
    )

    llm._make_request = AsyncMock(side_effect=rate_limit_err)

    from core.llm.base import APIError

    with pytest.raises(APIError, match="Insufficient funds"):
        await llm(convo)
