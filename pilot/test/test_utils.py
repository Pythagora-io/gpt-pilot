from unittest.mock import Mock


def mock_terminal_size():
    mock_size = Mock()
    mock_size.columns = 80  # or whatever width you want
    return mock_size

def assert_non_empty_string(value):
    assert isinstance(value, str)
    assert len(value) > 0
