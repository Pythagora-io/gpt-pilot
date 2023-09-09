import pytest
from unittest.mock import patch, mock_open
import uuid
from .arguments import get_email, username_to_uuid


def test_email_found_in_gitconfig():
    mock_file_content = """
    [user]
        name = test_user
        email = test@example.com
    """
    with patch('builtins.open', mock_open(read_data=mock_file_content)):
        assert get_email() == "test@example.com"


def test_email_not_found_in_gitconfig():
    mock_file_content = """
    [user]
        name = test_user
    """
    mock_uuid = "12345678-1234-5678-1234-567812345678"

    with patch('builtins.open', mock_open(read_data=mock_file_content)):
        with patch.object(uuid, "uuid4", return_value=mock_uuid):
            assert get_email() == mock_uuid


def test_gitconfig_not_present():
    mock_uuid = "12345678-1234-5678-1234-567812345678"

    with patch('os.path.exists', return_value=False):
        with patch.object(uuid, "uuid4", return_value=mock_uuid):
            assert get_email() == mock_uuid


def test_username_to_uuid():
    assert username_to_uuid("test_user") == "31676025-316f-b555-e0bf-a12f0bcfd0ea"
