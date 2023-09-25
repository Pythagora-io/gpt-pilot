from unittest.mock import Mock

def mock_terminal_size():
    """
    from test.mock_terminal_size import mock_terminal_size
    @patch('os.get_terminal_size', mock_terminal_size)
    """
    mock_size = Mock()
    mock_size.columns = 80  # or whatever width you want
    return mock_size
