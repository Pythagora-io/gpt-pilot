from unittest.mock import Mock
from .utils import should_execute_step


class TestShouldExecuteStep:
    def test_no_step_arg(self):
        assert should_execute_step(None, 'project_description') is True
        assert should_execute_step(None, 'architecture') is True
        assert should_execute_step(None, 'coding') is True

    def test_skip_step(self):
        assert should_execute_step('architecture', 'project_description') is False
        assert should_execute_step('architecture', 'architecture') is True
        assert should_execute_step('architecture', 'coding') is True

    def test_unknown_step(self):
        assert should_execute_step('architecture', 'unknown') is False
        assert should_execute_step('unknown', 'project_description') is False
        assert should_execute_step('unknown', None) is False
        assert should_execute_step(None, None) is False


def mock_terminal_size():
    mock_size = Mock()
    mock_size.columns = 80  # or whatever width you want
    return mock_size
