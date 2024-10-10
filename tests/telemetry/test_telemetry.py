from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
import pytest_asyncio

from core.config import loader
from core.telemetry import Telemetry


@pytest_asyncio.fixture
async def mock_httpx_post():
    with patch("core.telemetry.httpx") as mock_httpx:
        mock_httpx.RequestError = httpx.RequestError
        mock_client = mock_httpx.AsyncClient.return_value
        mock_async_with = mock_client.__aenter__.return_value
        mock_post = mock_async_with.post = AsyncMock(return_value=MagicMock())
        yield mock_post


@patch("core.telemetry.sys.platform", "test_platform")
@patch("core.telemetry.sys.version", "test_version")
@patch("core.telemetry.get_version", lambda: "test_pilot_version")
def test_clear_data_resets_data():
    telemetry = Telemetry()
    empty = Telemetry()

    telemetry.data = {
        "model": "test-model",
        "num_llm_requests": 10,
        "num_llm_tokens": 100,
        "num_steps": 5,
        "elapsed_time": 123.45,
        "end_result": "success",
        "user_feedback": "Great!",
        "user_contact": "user@example.com",
    }
    assert telemetry.data != empty.data

    telemetry.clear_data()

    assert telemetry.data == empty.data


def test_clear_data_resets_times():
    telemetry = Telemetry()
    telemetry.start_time = 1234567890
    telemetry.end_time = 1234567895

    telemetry.clear_data()

    assert telemetry.start_time is None
    assert telemetry.end_time is None


def test_clear_counter_resets_times_but_leaves_data():
    telemetry = Telemetry()
    telemetry.data["model"] = "test-model"
    telemetry.start_time = 1234567890
    telemetry.end_time = 1234567895

    telemetry.clear_counters()

    assert telemetry.data["model"] == "test-model"
    assert telemetry.start_time is None
    assert telemetry.end_time is None


@patch("core.telemetry.settings")
def test_set_updates_data(mock_settings):
    mock_settings.telemetry = MagicMock(id="test-id", endpoint="test-endpoint", enabled=True)
    telemetry = Telemetry()
    telemetry.set("model", "fake-model")
    assert telemetry.data["model"] == "fake-model"


@patch("core.telemetry.settings")
def test_set_ignores_unknown_field(mock_settings):
    mock_settings.telemetry = MagicMock(id="test-id", endpoint="test-endpoint", enabled=True)
    telemetry = Telemetry()
    telemetry.set("nonexistent_field", "value")
    assert "nonexistent_field" not in telemetry.data


@patch("core.telemetry.settings")
def test_inc_increments_known_data_field(mock_settings):
    mock_settings.telemetry = MagicMock(id="test-id", endpoint="test-endpoint", enabled=True)
    telemetry = Telemetry()
    telemetry.inc("num_llm_requests", 42)
    assert telemetry.data["num_llm_requests"] == 42


@patch("core.telemetry.settings")
def test_inc_ignores_unknown_data_field(mock_settings):
    mock_settings.telemetry = MagicMock(id="test-id", endpoint="test-endpoint", enabled=True)
    telemetry = Telemetry()
    telemetry.inc("unknown_field")
    assert "unknown_field" not in telemetry.data


@patch("core.telemetry.getenv")
@patch("core.telemetry.time")
@patch("core.telemetry.settings")
def test_start_with_telemetry_enabled(mock_settings, mock_time, mock_getenv):
    mock_settings.telemetry = MagicMock(id="test-id", endpoint="test-endpoint", enabled=True)
    mock_time.time.return_value = 1234.0
    mock_getenv.return_value = None  # override DISABLE_TELEMETRY test env var

    telemetry = Telemetry()
    telemetry.start()
    assert telemetry.start_time == 1234.0


@patch("core.telemetry.settings")
def test_stop_when_not_enabled_does_nothing(mock_settings):
    mock_settings.telemetry = MagicMock(id="test-id", endpoint="test-endpoint", enabled=False)

    telemetry = Telemetry()
    telemetry.stop()

    assert telemetry.end_time is None


@patch("core.telemetry.time")
@patch("core.telemetry.settings")
def test_stop_calculates_elapsed_time(mock_settings, mock_time):
    mock_settings.telemetry = MagicMock(id="test-id", endpoint="test-endpoint", enabled=True)
    mock_time.time.side_effect = [1234, 1235]
    telemetry = Telemetry()

    telemetry.start()
    telemetry.stop()

    assert telemetry.data["elapsed_time"] == 1


@pytest.mark.asyncio
@patch("core.telemetry.getenv")
@patch("core.telemetry.settings")
async def test_send_enabled_and_successful(mock_settings, mock_getenv, mock_httpx_post):
    mock_settings.telemetry = MagicMock(id="test-id", endpoint="test-endpoint", enabled=True)
    mock_getenv.return_value = None  # override DISABLE_TELEMETRY test env var

    telemetry = Telemetry()
    with patch.object(telemetry, "calculate_statistics"):
        await telemetry.send()

    expected = {
        "pathId": "test-id",
        "event": "pythagora-core-telemetry",
        "data": telemetry.data,
    }
    mock_httpx_post.assert_awaited_once_with("test-endpoint", json=expected)


@pytest.mark.asyncio
@patch("core.telemetry.getenv")
@patch("core.telemetry.settings")
async def test_send_enabled_but_post_fails(mock_settings, mock_getenv, mock_httpx_post):
    mock_settings.telemetry = MagicMock(id="test-id", endpoint="test-endpoint", enabled=True)
    mock_httpx_post.side_effect = httpx.RequestError("Connection error")
    mock_getenv.return_value = None  # override DISABLE_TELEMETRY test env var

    telemetry = Telemetry()
    with patch.object(telemetry, "calculate_statistics"):
        await telemetry.send()

    expected = {
        "pathId": "test-id",
        "event": "pythagora-core-telemetry",
        "data": telemetry.data,
    }
    mock_httpx_post.assert_awaited_once_with(telemetry.endpoint, json=expected)


@pytest.mark.asyncio
@patch("core.telemetry.settings")
async def test_send_not_enabled(mock_settings, mock_httpx_post):
    mock_settings.telemetry = MagicMock(id="test-id", endpoint="test-endpoint", enabled=False)

    telemetry = Telemetry()
    await telemetry.send()

    mock_httpx_post.assert_not_called()


@pytest.mark.asyncio
@patch("core.telemetry.getenv")
@patch("core.telemetry.settings")
async def test_send_no_endpoint_configured(mock_settings, mock_getenv, mock_httpx_post):
    mock_settings.telemetry = MagicMock(id="test-id", endpoint=None, enabled=True)
    mock_getenv.return_value = None  # override DISABLE_TELEMETRY test env var

    telemetry = Telemetry()
    await telemetry.send()

    mock_httpx_post.assert_not_called()


@pytest.mark.asyncio
@patch("core.telemetry.getenv")
@patch("core.telemetry.settings")
async def test_send_clears_counters_after_sending(mock_settings, mock_getenv, mock_httpx_post):
    mock_settings.telemetry = MagicMock(id="test-id", endpoint="test-endpoint", enabled=True)
    mock_getenv.return_value = None  # override DISABLE_TELEMETRY test env var

    telemetry = Telemetry()
    telemetry.data["model"] = "test-model"
    telemetry.data["num_llm_tokens"] = 100
    await telemetry.send()

    assert telemetry.data["model"] == "test-model"
    assert telemetry.data["num_llm_tokens"] == 0


@patch("core.telemetry.settings")
def test_record_crash(mock_settings):
    mock_settings.telemetry = MagicMock(id="test-id", endpoint="test-endpoint", enabled=True)

    telemetry = Telemetry()
    try:
        loader.load("/tmp/this/file/does/not/exist")
    except Exception as err:
        telemetry.record_crash(err)

    assert telemetry.data["end_result"] == "failure"
    diag = telemetry.data["crash_diagnostics"]
    assert diag["exception_class"] == "FileNotFoundError"
    assert "/tmp/this/file/does/not/exist" in diag["exception_message"]
    assert diag["frames"][0]["file"] == "core/config/__init__.py"
    assert "FileNotFoundError" in diag["stack_trace"]


@patch("core.telemetry.settings")
def test_record_llm_request(mock_settings):
    mock_settings.telemetry = MagicMock(id="test-id", endpoint="test-endpoint", enabled=True)

    telemetry = Telemetry()
    telemetry.record_llm_request(100000, 3600, True)
    telemetry.record_llm_request(90000, 1, False)
    telemetry.record_llm_request(1, 1800, False)

    # All three
    assert telemetry.data["num_llm_requests"] == 3
    # Only the last two
    assert telemetry.data["num_llm_tokens"] == 90001
    # Only the first one
    assert telemetry.data["num_llm_errors"] == 1

    # First two
    assert telemetry.large_requests == [100000, 90000]
    # FIrst and last
    assert telemetry.slow_requests == [3600, 1800]


@patch("core.telemetry.settings")
def test_calculate_statistics(mock_settings):
    mock_settings.telemetry = MagicMock(id="test-id", endpoint="test-endpoint", enabled=True)

    telemetry = Telemetry()
    telemetry.large_requests = [10, 10, 20, 40, 100]
    telemetry.slow_requests = [10, 10, 20, 40, 100]

    telemetry.calculate_statistics()
    assert telemetry.data["large_requests"] == {
        "num_requests": 5,
        "min_tokens": 10,
        "max_tokens": 100,
        "avg_tokens": 36,
        "median_tokens": 20,
    }
    assert telemetry.data["slow_requests"] == {
        "num_requests": 5,
        "min_time": 10,
        "max_time": 100,
        "avg_time": 36,
        "median_time": 20,
    }
