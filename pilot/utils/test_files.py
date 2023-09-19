import pytest
from .files import setup_workspace


def test_setup_workspace_with_existing_workspace():
    args = {'workspace': 'some_directory', 'name': 'sample'}
    result = setup_workspace(args)
    assert result == 'some_directory'


def mocked_create_directory(path, exist_ok=True):
    return


def mocked_abspath(file):
    return "/root_path/pilot/helpers"


def test_setup_workspace_without_existing_workspace(monkeypatch):
    args = {'workspace': None, 'name': 'project_name'}

    monkeypatch.setattr('os.path.abspath', mocked_abspath)
    monkeypatch.setattr('os.makedirs', mocked_create_directory)

    result = setup_workspace(args)
    assert result.replace('\\', '/') == "/root_path/workspace/project_name"
