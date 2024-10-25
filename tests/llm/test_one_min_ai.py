from unittest.mock import MagicMock, patch
import pytest
from core.config import LLMConfig
from core.llm.convo import Convo
from core.llm.oneminai_client import OneMinAIClient  # Updated import
from requests.exceptions import HTTPError


@pytest.mark.asyncio
@patch("requests.post")  # Mock `requests.post` instead of `AsyncOpenAI`
async def test_oneminai_calls_model(mock_post):
    cfg = LLMConfig(model="1minai-model")
    convo = Convo("system hello").user("user hello")

    # Mock the return value of `requests.post`
    mock_post.return_value.status_code = 200
    mock_post.return_value.text = "helloworld"  # Simulate plain text response

    llm = OneMinAIClient(cfg)
    response = await llm._make_request(convo)

    assert response == "helloworld"

    mock_post.assert_called_once_with(
        cfg.base_url,
        json={
            "type": "CHAT_WITH_AI",
            "conversationId": cfg.extra.get("conversation_id"),
            "model": cfg.model,
            "promptObject": {
                "prompt": "system hello user hello",  # Combined messages
                "isMixed": False,
                "webSearch": False
            }
        },
        headers={"API-KEY": cfg.api_key, "Content-Type": "application/json"},
        timeout=(cfg.connect_timeout, cfg.read_timeout),
    )


@pytest.mark.asyncio
@patch("requests.post")
async def test_oneminai_error_handler(mock_post):
    cfg = LLMConfig(model="1minai-model")
    convo = Convo("system hello").user("user hello")

    # Simulate a failed request
    mock_post.return_value.status_code = 500
    mock_post.return_value.text = "Internal Server Error"

    llm = OneMinAIClient(cfg)

    with pytest.raises(HTTPError):
        await llm._make_request(convo)


@pytest.mark.asyncio
@patch("requests.post")
async def test_oneminai_retry_logic(mock_post):
    cfg = LLMConfig(model="1minai-model")
    convo = Convo("system hello").user("user hello")

    # Simulate failure on the first attempt and success on the second
    mock_post.side_effect = [
        MagicMock(status_code=500, text="Error"),  # First call fails
        MagicMock(status_code=200, text="Hello"),  # Second call succeeds
    ]

    llm = OneMinAIClient(cfg)
    response = await llm._make_request(convo)

    assert response == "Hello"
    assert mock_post.call_count == 2


@pytest.mark.parametrize(
    ("remaining_tokens", "reset_tokens", "reset_requests", "expected"),
    [
        (0, "1h1m1s", "", 3661),
        (0, "1h1s", "", 3601),
        (0, "1m", "", 60),
        (0, "", "1h1m1s", 0),
        (1, "", "1h1m1s", 3661),
    ],
)
@patch("requests.post")
def test_oneminai_rate_limit_parser(mock_post, remaining_tokens, reset_tokens, reset_requests, expected):
    headers = {
        "x-ratelimit-remaining-tokens": remaining_tokens,
        "x-ratelimit-reset-tokens": reset_tokens,
        "x-ratelimit-reset-requests": reset_requests,
    }
    err = MagicMock(response=MagicMock(headers=headers))

    llm = OneMinAIClient(LLMConfig(model="1minai-model"))
    assert int(llm.rate_limit_sleep(err).total_seconds()) == expected


@pytest.mark.asyncio
@patch("requests.post")
async def test_oneminai_response_success(mock_post):
    cfg = LLMConfig(model="1minai-model")
    convo = Convo("system hello").user("user hello")

    # Simulate a successful response
    mock_post.return_value.status_code = 200
    mock_post.return_value.text = "Success"

    llm = OneMinAIClient(cfg)
    response = await llm._make_request(convo)

    assert response == "Success"
    mock_post.assert_called_once()


@pytest.mark.asyncio
@patch("requests.post")
async def test_oneminai_handle_non_200_response(mock_post):
    cfg = LLMConfig(model="1minai-model")
    convo = Convo("system hello").user("user hello")

    # Simulate a non-200 response
    mock_post.return_value.status_code = 400
    mock_post.return_value.text = "Bad Request"

    llm = OneMinAIClient(cfg)

    with pytest.raises(HTTPError):
        await llm._make_request(convo)

    mock_post.assert_called_once()