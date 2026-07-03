from unittest.mock import AsyncMock, patch

import httpx
import pytest

from core.config import Config, DakeraConfig
from core.memory import ProjectMemory

RECALL_RESPONSE = {
    "memories": [
        {
            "memory": {"content": "Use Optional types on the user schema", "importance": 0.8},
            "score": 0.42,
            "weighted_score": 0.51,
        },
        {
            "memory": {"content": "Auth tokens live in the Authorization header"},
            "score": 0.31,
        },
        # A malformed entry with no content must be skipped, not crash.
        {"memory": {}, "score": 0.1},
    ]
}


def _config(**overrides) -> DakeraConfig:
    return DakeraConfig(**overrides)


def _ok(json_body: dict) -> httpx.Response:
    # A request must be attached for Response.raise_for_status() to work.
    return httpx.Response(200, json=json_body, request=httpx.Request("POST", "http://localhost:3000"))


def _post_mock(response: httpx.Response) -> AsyncMock:
    return AsyncMock(return_value=response)


def test_for_project_returns_none_when_memory_unconfigured():
    with patch("core.memory.get_config", return_value=Config()):
        assert ProjectMemory.for_project("abc") is None


def test_for_project_returns_none_when_disabled():
    cfg = Config(memory=_config(enabled=False))
    with patch("core.memory.get_config", return_value=cfg):
        assert ProjectMemory.for_project("abc") is None


def test_for_project_returns_none_without_project_id():
    cfg = Config(memory=_config())
    with patch("core.memory.get_config", return_value=cfg):
        assert ProjectMemory.for_project(None) is None


def test_for_project_builds_namespaced_client():
    cfg = Config(memory=_config())
    with patch("core.memory.get_config", return_value=cfg):
        memory = ProjectMemory.for_project("proj-123")
    assert isinstance(memory, ProjectMemory)
    assert memory.agent_id == "gptpilot-proj-123"


@pytest.mark.asyncio
async def test_recall_parses_and_orders_memories():
    memory = ProjectMemory(_config(top_k=3), "p1")
    response = _ok(RECALL_RESPONSE)
    with patch.object(httpx.AsyncClient, "post", _post_mock(response)) as mock_post:
        recalled = await memory.recall("implement user auth")

    # The malformed (content-less) entry is dropped.
    assert [m.content for m in recalled] == [
        "Use Optional types on the user schema",
        "Auth tokens live in the Authorization header",
    ]
    # Weighted score preferred when present, plain score otherwise.
    assert recalled[0].score == 0.51
    assert recalled[1].score == 0.31

    url, kwargs = mock_post.call_args.args[0], mock_post.call_args.kwargs
    assert url.endswith("/v1/memory/recall")
    assert kwargs["json"] == {"agent_id": "gptpilot-p1", "query": "implement user auth", "top_k": 3}


@pytest.mark.asyncio
async def test_recall_sends_api_key_header_when_configured():
    memory = ProjectMemory(_config(api_key="dk-secret"), "p1")
    response = _ok({"memories": []})
    with patch.object(httpx.AsyncClient, "post", _post_mock(response)) as mock_post:
        await memory.recall("anything")
    assert mock_post.call_args.kwargs["headers"]["X-API-Key"] == "dk-secret"


@pytest.mark.asyncio
async def test_recall_omits_api_key_header_when_absent():
    memory = ProjectMemory(_config(), "p1")
    response = _ok({"memories": []})
    with patch.object(httpx.AsyncClient, "post", _post_mock(response)) as mock_post:
        await memory.recall("anything")
    assert "X-API-Key" not in mock_post.call_args.kwargs["headers"]


@pytest.mark.asyncio
async def test_recall_returns_empty_on_network_error():
    memory = ProjectMemory(_config(), "p1")
    with patch.object(httpx.AsyncClient, "post", AsyncMock(side_effect=httpx.ConnectError("down"))):
        assert await memory.recall("anything") == []


@pytest.mark.asyncio
async def test_recall_returns_empty_for_blank_query():
    memory = ProjectMemory(_config(), "p1")
    with patch.object(httpx.AsyncClient, "post", AsyncMock()) as mock_post:
        assert await memory.recall("") == []
    mock_post.assert_not_called()


@pytest.mark.asyncio
async def test_store_posts_expected_payload():
    memory = ProjectMemory(_config(min_importance=0.7), "p1")
    response = _ok({"memory": {"id": "m1"}, "embedding_time_ms": 1})
    with patch.object(httpx.AsyncClient, "post", _post_mock(response)) as mock_post:
        ok = await memory.store("Task: build login", tags=["gpt-pilot", "task-outcome"])

    assert ok is True
    url, kwargs = mock_post.call_args.args[0], mock_post.call_args.kwargs
    assert url.endswith("/v1/memory/store")
    assert kwargs["json"] == {
        "agent_id": "gptpilot-p1",
        "content": "Task: build login",
        "importance": 0.7,
        "tags": ["gpt-pilot", "task-outcome"],
    }


@pytest.mark.asyncio
async def test_store_includes_lifecycle_metadata_when_provided():
    memory = ProjectMemory(_config(), "p1")
    response = _ok({"memory": {"id": "m1"}, "embedding_time_ms": 1})
    metadata = {"kind": "bug_fix", "status": "candidate", "source": "gpt-pilot"}
    with patch.object(httpx.AsyncClient, "post", _post_mock(response)) as mock_post:
        ok = await memory.store("Task: fix login", tags=["gpt-pilot"], metadata=metadata)

    assert ok is True
    assert mock_post.call_args.kwargs["json"]["metadata"] == metadata


@pytest.mark.asyncio
async def test_store_omits_metadata_when_absent():
    memory = ProjectMemory(_config(), "p1")
    response = _ok({"memory": {"id": "m1"}, "embedding_time_ms": 1})
    with patch.object(httpx.AsyncClient, "post", _post_mock(response)) as mock_post:
        await memory.store("Task: build login")
    assert "metadata" not in mock_post.call_args.kwargs["json"]


@pytest.mark.asyncio
async def test_store_returns_false_on_network_error():
    memory = ProjectMemory(_config(), "p1")
    with patch.object(httpx.AsyncClient, "post", AsyncMock(side_effect=httpx.ConnectError("down"))):
        assert await memory.store("Task: build login") is False


@pytest.mark.asyncio
async def test_store_skips_empty_content():
    memory = ProjectMemory(_config(), "p1")
    with patch.object(httpx.AsyncClient, "post", AsyncMock()) as mock_post:
        assert await memory.store("") is False
    mock_post.assert_not_called()
