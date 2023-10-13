import os
from unittest.mock import patch
from utils.files import setup_workspace


def mocked_create_directory(path, exist_ok=True):
    return


def mocked_abspath(file):
    return "/root_path/pilot/helpers"


@patch('utils.files.os.makedirs', side_effect=mocked_create_directory)
def test_setup_workspace_with_existing_workspace(mock_makedirs):
    args = {'workspace': '/some/directory', 'name': 'sample'}
    result = setup_workspace(args)
    assert result == '/some/directory'


def test_setup_workspace_with_root_arg(monkeypatch):
    args = {'root': '/my/root', 'name': 'project_name'}

    monkeypatch.setattr('os.path.abspath', mocked_abspath)
    monkeypatch.setattr('os.makedirs', mocked_create_directory)

    result = setup_workspace(args)
    assert result.replace('\\', '/') == "/my/root/workspace/project_name"


@patch('utils.files.os.path.abspath', return_value='/root_path/pilot/helpers')
@patch('utils.files.os.makedirs', side_effect=mocked_create_directory)
def test_setup_workspace_without_existing_workspace(mock_makedirs, mock_abs_path):
    args = {'workspace': None, 'name': 'project_name'}

    result = setup_workspace(args)
    assert result.replace('\\', '/') == "/root_path/workspace/project_name"
