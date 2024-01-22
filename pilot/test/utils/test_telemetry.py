from unittest.mock import patch


from utils.telemetry import Telemetry


@patch("utils.telemetry.settings")
def test_telemetry_constructor_with_telemetry_enabled(mock_settings):
    mock_settings.telemetry = {
        "id": "test-id",
        "endpoint": "test-endpoint",
        "enabled": True,
    }
    telemetry = Telemetry()
    assert telemetry.enabled
    assert telemetry.telemetry_id == "test-id"
    assert telemetry.endpoint == "test-endpoint"


@patch("utils.telemetry.settings")
def test_telemetry_constructor_with_telemetry_disabled(mock_settings):
    mock_settings.telemetry = {"id": "existing-id", "enabled": False}
    telemetry = Telemetry()
    assert not telemetry.enabled


@patch("utils.telemetry.settings")
def test_telemetry_constructor_with_telemetry_not_configured(mock_settings):
    mock_settings.telemetry = None
    telemetry = Telemetry()
    assert not telemetry.enabled


@patch("utils.telemetry.config_path", "/path/to/config")
@patch("utils.telemetry.settings")
def test_telemetry_constructor_logging_enabled(mock_settings, caplog):
    caplog.set_level("DEBUG")
    mock_settings.telemetry = {
        "id": "test-id",
        "endpoint": "test-endpoint",
        "enabled": True,
    }
    Telemetry()
    assert (
        "Anonymous telemetry enabled (id=test-id), configure or disable it in /path/to/config"
        in caplog.text
    )


@patch("utils.telemetry.sys.platform", "test_platform")
@patch("utils.telemetry.sys.version", "test_version")
@patch("utils.telemetry.version", "test_pilot_version")
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


@patch("utils.telemetry.settings")
@patch("utils.telemetry.uuid4")
def test_telemetry_setup_already_enabled(mock_uuid4, mock_settings):
    mock_settings.telemetry = {"id": "existing-id", "enabled": True}
    telemetry = Telemetry()
    telemetry.setup()
    mock_uuid4.assert_not_called()


@patch("utils.telemetry.settings")
@patch("utils.telemetry.uuid4")
def test_telemetry_setup_enable(mock_uuid4, mock_settings):
    mock_settings.telemetry = {"id": "existing-id", "enabled": False}
    mock_uuid4.return_value = "fake-id"
    telemetry = Telemetry()
    telemetry.setup()

    mock_uuid4.assert_called_once()
    assert telemetry.telemetry_id == "telemetry-fake-id"

    assert mock_settings.telemetry == {
        "id": "telemetry-fake-id",
        "endpoint": Telemetry.DEFAULT_ENDPOINT,
        "enabled": True,
    }


@patch("utils.telemetry.settings")
def test_set_ignores_data_if_disabled(mock_settings):
    mock_settings.telemetry = {"id": "existing-id", "enabled": False}
    telemetry = Telemetry()
    telemetry.set("model", "fake-model")
    assert telemetry.data.get("model") != "fake-model"


@patch("utils.telemetry.settings")
def test_set_updates_data_if_enabled(mock_settings):
    mock_settings.telemetry = {
        "id": "test-id",
        "endpoint": "test-endpoint",
        "enabled": True,
    }
    telemetry = Telemetry()
    telemetry.set("model", "fake-model")
    assert telemetry.data["model"] == "fake-model"


@patch("utils.telemetry.settings")
def test_set_ignores_unknown_field(mock_settings):
    mock_settings.telemetry = {
        "id": "test-id",
        "endpoint": "test-endpoint",
        "enabled": True,
    }
    telemetry = Telemetry()
    telemetry.set("nonexistent_field", "value")
    assert "nonexistent_field" not in telemetry.data


@patch("utils.telemetry.settings")
def test_inc_increments_known_data_field(mock_settings):
    mock_settings.telemetry = {
        "id": "test-id",
        "endpoint": "test-endpoint",
        "enabled": True,
    }
    telemetry = Telemetry()
    telemetry.inc("num_llm_requests", 42)
    assert telemetry.data["num_llm_requests"] == 42


@patch("utils.telemetry.settings")
def test_inc_does_not_increment_when_disabled(mock_settings):
    mock_settings.telemetry = {"id": "existing-id", "enabled": False}
    telemetry = Telemetry()
    telemetry.inc("num_llm_requests", 42)
    assert telemetry.data["num_llm_requests"] == 0


@patch("utils.telemetry.settings")
def test_inc_ignores_unknown_data_field(mock_settings):
    mock_settings.telemetry = {
        "id": "test-id",
        "endpoint": "test-endpoint",
        "enabled": True,
    }
    telemetry = Telemetry()
    telemetry.inc("unknown_field")
    assert "unknown_field" not in telemetry.data


@patch("utils.telemetry.settings")
def test_start_with_telemetry_disabled(mock_settings):
    mock_settings.telemetry = {"id": "existing-id", "enabled": False}
    telemetry = Telemetry()
    telemetry.start()
    assert telemetry.start_time is None


@patch("utils.telemetry.time")
@patch("utils.telemetry.settings")
def test_start_with_telemetry_enabled(mock_settings, mock_time):
    mock_settings.telemetry = {
        "id": "test-id",
        "endpoint": "test-endpoint",
        "enabled": True,
    }
    mock_time.time.return_value = 1234.0

    telemetry = Telemetry()

    telemetry.start()
    assert telemetry.start_time == 1234.0


@patch("utils.telemetry.settings")
def test_stop_when_not_enabled_does_nothing(mock_settings):
    mock_settings.telemetry = {"id": "existing-id", "enabled": False}

    telemetry = Telemetry()
    telemetry.stop()

    assert telemetry.end_time is None


@patch("utils.telemetry.settings")
def test_stop_without_start_logs_error(mock_settings, caplog):
    mock_settings.telemetry = {
        "id": "test-id",
        "endpoint": "test-endpoint",
        "enabled": True,
    }
    telemetry = Telemetry()
    telemetry.stop()
    assert "it was never started" in caplog.text


@patch("utils.telemetry.time")
@patch("utils.telemetry.settings")
def test_stop_calculates_elapsed_time(mock_settings, mock_time):
    mock_settings.telemetry = {
        "id": "test-id",
        "endpoint": "test-endpoint",
        "enabled": True,
    }
    mock_time.time.side_effect = [1234, 1235]
    telemetry = Telemetry()

    telemetry.start()
    telemetry.stop()

    assert telemetry.data["elapsed_time"] == 1


@patch("utils.telemetry.requests.post")
@patch("utils.telemetry.settings")
def test_send_enabled_and_successful(mock_settings, mock_post, caplog):
    caplog.set_level("DEBUG")
    mock_settings.telemetry = {
        "id": "test-id",
        "endpoint": "test-endpoint",
        "enabled": True,
    }

    telemetry = Telemetry()
    with patch.object(telemetry, "calculate_statistics"):
        telemetry.send()

    expected = {
        "pathId": "test-id",
        "event": "pilot-telemetry",
        "data": telemetry.data,
    }
    mock_post.assert_called_once_with("test-endpoint", json=expected)
    assert "sending anonymous telemetry data to test-endpoint" in caplog.text


@patch("utils.telemetry.requests.post")
@patch("utils.telemetry.settings")
def test_send_enabled_but_post_fails(mock_settings, mock_post):
    mock_settings.telemetry = {
        "id": "test-id",
        "endpoint": "test-endpoint",
        "enabled": True,
    }
    mock_post.side_effect = Exception("Connection error")

    telemetry = Telemetry()
    with patch.object(telemetry, "calculate_statistics"):
        telemetry.send()

    expected = {
        "pathId": "test-id",
        "event": "pilot-telemetry",
        "data": telemetry.data,
    }
    mock_post.assert_called_once_with(telemetry.endpoint, json=expected)


@patch("utils.telemetry.requests.post")
@patch("utils.telemetry.settings")
def test_send_not_enabled(mock_settings, mock_post):
    mock_settings.telemetry = {
        "id": "test-id",
        "endpoint": "test-endpoint",
        "enabled": False,
    }

    telemetry = Telemetry()
    telemetry.send()

    mock_post.assert_not_called()


@patch("utils.telemetry.requests.post")
@patch("utils.telemetry.settings")
def test_send_no_endpoint_configured(mock_settings, mock_post, caplog):
    mock_settings.telemetry = {"id": "test-id", "endpoint": None, "enabled": True}

    telemetry = Telemetry()
    telemetry.send()

    mock_post.assert_not_called()
    assert "cannot send telemetry, no endpoint configured" in caplog.text


@patch("utils.telemetry.requests.post")
@patch("utils.telemetry.settings")
def test_send_clears_counters_after_sending(mock_settings, _mock_post):
    mock_settings.telemetry = {
        "id": "test-id",
        "endpoint": "test-endpoint",
        "enabled": True,
    }

    telemetry = Telemetry()
    telemetry.data["model"] = "test-model"
    telemetry.data["num_llm_tokens"] = 100
    telemetry.send()

    assert telemetry.data["model"] == "test-model"
    assert telemetry.data["num_llm_tokens"] == 0


@patch("utils.telemetry.settings")
def test_record_crash(mock_settings):
    mock_settings.telemetry = {
        "id": "test-id",
        "endpoint": "test-endpoint",
        "enabled": True,
    }

    telemetry = Telemetry()
    try:
        raise ValueError("test error")
    except Exception as err:
        telemetry.record_crash(err)

    assert telemetry.data["end_result"] == "failure"
    diag = telemetry.data["crash_diagnostics"]
    assert diag["exception_class"] == "ValueError"
    assert diag["exception_message"] == "test error"
    assert diag["frames"][0]["file"] == "pilot/test/utils/test_telemetry.py"
    assert "ValueError: test error" in diag["stack_trace"]


@patch("utils.telemetry.settings")
def test_record_crash_crashes(mock_settings):
    mock_settings.telemetry = {
        "id": "test-id",
        "endpoint": "test-endpoint",
        "enabled": True,
    }

    telemetry = Telemetry()
    telemetry.record_crash(None)

    assert telemetry.data["end_result"] == "failure"
    diag = telemetry.data["crash_diagnostics"]
    assert diag["exception_class"] == "NoneType"
    assert diag["exception_message"] == "None"
    assert diag["frames"] == []


@patch("utils.telemetry.settings")
def test_record_llm_request(mock_settings):
    mock_settings.telemetry = {
        "id": "test-id",
        "endpoint": "test-endpoint",
        "enabled": True,
    }

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



@patch("utils.telemetry.settings")
def test_calculate_statistics(mock_settings):
    mock_settings.telemetry = {
        "id": "test-id",
        "endpoint": "test-endpoint",
        "enabled": True,
    }

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
