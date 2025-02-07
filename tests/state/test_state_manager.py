import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.config import FileSystemConfig
from core.state.state_manager import StateManager


@pytest.mark.asyncio
async def test_list_projects_empty(testmanager):
    sm = StateManager(testmanager)
    projects = await sm.list_projects()
    assert projects == []


@pytest.mark.asyncio
@patch("core.state.state_manager.get_config")
async def test_create_project(mock_get_config, testmanager):
    mock_get_config.return_value.fs.type = "memory"
    sm = StateManager(testmanager)
    project = await sm.create_project("test")

    async with testmanager as session:
        session.add(project)
        branch = await project.get_branch()
        initial_state = await branch.get_last_state()

    assert sm.project == project
    assert sm.branch == branch
    assert sm.current_state == initial_state

    projects = await sm.list_projects()
    assert projects == [project]


@pytest.mark.asyncio
@patch("core.state.state_manager.get_config")
async def test_load_project(mock_get_config, testmanager):
    mock_get_config.return_value.fs.type = "memory"
    sm = StateManager(testmanager)
    project = await sm.create_project("test")

    project_state = await sm.load_project(project_id=project.id)

    assert project_state.branch.project.id == project.id


@pytest.mark.asyncio
@patch("core.state.state_manager.get_config")
async def test_delete_project(mock_get_config, testmanager):
    mock_get_config.return_value.fs.type = "memory"
    sm = StateManager(testmanager)
    project = await sm.create_project("test")

    projects = await sm.list_projects()
    assert projects == [project]

    await sm.delete_project(project.id)
    projects = await sm.list_projects()
    assert projects == []


@pytest.mark.asyncio
@patch("core.state.state_manager.get_config")
async def test_load_project_branch(mock_get_config, testmanager):
    mock_get_config.return_value.fs.type = "memory"
    sm = StateManager(testmanager)
    project = await sm.create_project("test")

    project_state = await sm.load_project(branch_id=project.branches[0].id)

    assert project_state.branch.project.id == project.id


@pytest.mark.asyncio
@patch("core.state.state_manager.get_config")
async def test_load_nonexistent_step(mock_get_config, testmanager):
    mock_get_config.return_value.fs.type = "memory"
    sm = StateManager(testmanager)
    project = await sm.create_project("test")

    project_state = await sm.load_project(project_id=project.id, step_index=99999)
    assert project_state is None


@pytest.mark.asyncio
@patch("core.state.state_manager.get_config")
async def test_load_specific_step(mock_get_config, testmanager):
    mock_get_config.return_value.fs.type = "memory"
    sm = StateManager(testmanager)
    project = await sm.create_project("test")

    project_state = await sm.load_project(project_id=project.id, step_index=project.branches[0].states[0].step_index)

    assert project_state.branch.project.id == project.id


@pytest.mark.asyncio
@patch("core.state.state_manager.get_config")
async def test_commit(mock_get_config, testmanager):
    mock_get_config.return_value.fs.type = "memory"
    sm = StateManager(testmanager)
    project = await sm.create_project("test")

    initial_state = project.branches[0].states[0]
    sm.next_state.epics = [{"id": "epic-123"}]
    sm.next_state.tasks = [{"id": "task-456"}]
    sm.next_state.iterations = [{"id": "iteration-789"}]
    sm.next_state.steps = [{"id": "step-012"}]

    new_state = await sm.commit()

    # Initial state is special in that when it gets commited, we're
    # still on the same state.
    assert new_state.id == initial_state.id
    assert new_state.prev_state_id is None

    # The 2nd commit will actually create a new state
    next_state = await sm.commit()
    assert next_state.id != new_state.id
    assert next_state.prev_state_id == new_state.id

    # Test that data was correctly copied over
    assert next_state.epics == [{"id": "epic-123"}]
    assert next_state.tasks == [{"id": "task-456"}]
    assert next_state.iterations == [{"id": "iteration-789"}]
    assert next_state.steps == [{"id": "step-012"}]


@pytest.mark.asyncio
@patch("core.state.state_manager.get_config")
async def test_save_file(mock_get_config, testmanager):
    mock_get_config.return_value.fs.type = "memory"

    # Setup the UI mock
    ui = MagicMock(open_editor=AsyncMock())

    # Create an instance of StateManager with mocked UI
    sm = StateManager(testmanager, ui)
    await sm.create_project("test")

    # The initial state in the project is weird because it's both current
    # and next, and this can play havoc with the SQLAlchemy session and
    # object caching. Commit it here to get that out of our way.
    await sm.commit()

    # Save the file and commit the new state to the database
    await sm.save_file("test.txt", "Hello, world!")
    await sm.commit()

    # Assert that UI's open_editor was called
    # ui.open_editor.assert_called_once_with("/test.txt")

    # Assert that file was saved to disk
    assert sm.file_system.read("test.txt") == "Hello, world!"

    # Assert that file was saved to database
    file = await sm.get_file_by_path("test.txt")
    assert file is not None
    assert file.content.content == "Hello, world!"


@pytest.mark.asyncio
@patch("core.state.state_manager.get_config")
async def test_importing_changed_files_to_db(mock_get_config, tmpdir, testmanager):
    mock_get_config.return_value.fs = FileSystemConfig(workspace_root=str(tmpdir))
    sm = StateManager(testmanager)
    project = await sm.create_project("test")

    async with testmanager as session:
        session.add(project)
        await sm.commit()
        await sm.save_file("file1.txt", "this is the content 1")
        await sm.save_file("file2.txt", "this is the content 2")
        await sm.save_file("file3.txt", "this is the content 3")
        await sm.commit()

        os.remove(os.path.join(tmpdir, "test", "file1.txt"))  # Remove the first file
        with open(os.path.join(tmpdir, "test", "file2.txt"), "a") as f:
            f.write("modified")  # Change the second file

        await sm.import_files()
        await sm.commit()

        assert not os.path.exists(os.path.join(tmpdir, "test", "file1.txt"))
        assert os.path.exists(os.path.join(tmpdir, "test", "file2.txt"))
        assert os.path.exists(os.path.join(tmpdir, "test", "file3.txt"))

        db_files = set(f.path for f in sm.current_state.files)
        assert "file1.txt" not in db_files
        assert "file2.txt" in db_files
        assert "file3.txt" in db_files


@pytest.mark.asyncio
@patch("core.state.state_manager.get_config")
async def test_restoring_files_from_db(mock_get_config, tmpdir, testmanager):
    mock_get_config.return_value.fs = FileSystemConfig(workspace_root=str(tmpdir))
    sm = StateManager(testmanager)
    project = await sm.create_project("test1")

    async with testmanager as session:
        session.add(project)
        await sm.commit()
        await sm.save_file("file1.txt", "this is the content 1")
        await sm.save_file("file2.txt", "this is the content 2")
        await sm.save_file("file3.txt", "this is the content 3")
        await sm.commit()

        os.remove(os.path.join(tmpdir, "test1", "file1.txt"))  # Remove the first file
        with open(os.path.join(tmpdir, "test1", "file2.txt"), "a") as f:
            f.write("modified")  # Change the second file
        await sm.restore_files()

        assert os.path.exists(os.path.join(tmpdir, "test1", "file1.txt"))
        assert os.path.exists(os.path.join(tmpdir, "test1", "file2.txt"))
        assert os.path.exists(os.path.join(tmpdir, "test1", "file3.txt"))

        assert open(os.path.join(tmpdir, "test1", "file1.txt")).read() == "this is the content 1"
        assert open(os.path.join(tmpdir, "test1", "file2.txt")).read() == "this is the content 2"
        assert open(os.path.join(tmpdir, "test1", "file3.txt")).read() == "this is the content 3"
