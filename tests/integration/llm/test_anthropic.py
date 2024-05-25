from json import loads
from os import getenv

import pytest

from core.config import LLMConfig, LLMProvider
from core.llm.anthropic_client import AnthropicClient
from core.llm.base import APIError
from core.llm.convo import Convo
from core.llm.request_log import LLMRequestStatus

run_integration_tests = getenv("INTEGRATION_TESTS", "").lower()
if run_integration_tests not in ["true", "yes", "1", "on"]:
    pytest.skip("Skipping integration tests", allow_module_level=True)

if not getenv("ANTHROPIC_API_KEY"):
    pytest.skip(
        "Skipping Anthropic integration tests: ANTHROPIC_API_KEY is not set",
        allow_module_level=True,
    )


@pytest.mark.asyncio
async def test_incorrect_key():
    cfg = LLMConfig(
        provider=LLMProvider.ANTHROPIC,
        model="claude-3-haiku-20240307",
        api_key="sk-incorrect",
        temperature=0.5,
    )

    async def print_handler(msg: str):
        print(msg)

    llm = AnthropicClient(cfg, stream_handler=print_handler)
    convo = Convo("you're a friendly assistant").user("tell me joke")

    with pytest.raises(APIError, match="invalid x-api-key"):
        await llm(convo)


@pytest.mark.asyncio
async def test_unknown_model():
    cfg = LLMConfig(
        provider=LLMProvider.ANTHROPIC,
        model="gpt-3.6-nonexistent",
        temperature=0.5,
    )

    llm = AnthropicClient(cfg)
    convo = Convo("you're a friendly assistant").user("tell me joke")

    with pytest.raises(APIError, match="model: gpt-3.6-nonexistent"):
        await llm(convo)


@pytest.mark.asyncio
async def test_anthropic_success():
    cfg = LLMConfig(
        provider=LLMProvider.ANTHROPIC,
        model="claude-3-haiku-20240307",
        temperature=0.5,
    )

    streamed_response = []

    async def stream_handler(content: str):
        if content:
            streamed_response.append(content)

    llm = AnthropicClient(cfg, stream_handler=stream_handler)
    convo = Convo("you're a friendly assistant").user("tell me joke")

    response, req_log = await llm(convo)
    assert response == "".join(streamed_response)

    assert req_log.messages == convo.messages
    assert req_log.prompt_tokens > 0
    assert req_log.completion_tokens > 0


@pytest.mark.asyncio
async def test_anthropic_json_mode():
    cfg = LLMConfig(
        provider=LLMProvider.ANTHROPIC,
        model="claude-3-haiku-20240307",
        temperature=0.5,
    )

    llm = AnthropicClient(cfg)
    convo = Convo("you're a friendly assistant")
    convo.user(
        "Tell me a q/a joke. "
        'Output it in a JSON format like: {"q": "...", "a": "..."}.'
        "Important, do not output anything except a valid JSON structure."
    )

    response, req_log = await llm(convo)

    data = loads(response)
    assert "q" in data
    assert "a" in data


@pytest.mark.asyncio
async def test_context_too_large():
    cfg = LLMConfig(
        provider=LLMProvider.ANTHROPIC,
        model="claude-3-haiku-20240307",
        temperature=0.5,
    )

    large_convo = " ".join(["lorem ipsum dolor sit amet"] * 60000)
    llm = AnthropicClient(cfg)
    convo = Convo("you're a friendly assistant")
    convo.user(large_convo)

    response, req_log = await llm(convo)
    assert response is None
    assert req_log.status == LLMRequestStatus.ERROR
