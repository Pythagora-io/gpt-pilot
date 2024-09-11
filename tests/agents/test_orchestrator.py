from unittest.mock import AsyncMock, Mock

import pytest

from core.agents.orchestrator import Orchestrator


@pytest.mark.asyncio
async def test_offline_changes_check_restores_if_workspace_empty():
    sm = AsyncMock()
    sm.workspace_is_empty = Mock(return_value=False)
    ui = AsyncMock()
    orca = Orchestrator(state_manager=sm, ui=ui)
    await orca.offline_changes_check()
    assert sm.restore_files.assert_called_once


@pytest.mark.asyncio
async def test_offline_changes_check_imports_changes_from_disk():
    sm = AsyncMock()
    sm.workspace_is_empty = Mock(return_value=False)
    sm.import_files = AsyncMock(return_value=([], []))
    ui = AsyncMock()
    ui.ask_question.return_value.button = "yes"
    orca = Orchestrator(state_manager=sm, ui=ui)
    await orca.offline_changes_check()
    assert sm.import_files.assert_called_once
    assert sm.restore_files.assert_not_called


@pytest.mark.asyncio
async def test_offline_changes_check_restores_changes_from_db():
    sm = AsyncMock()
    sm.workspace_is_empty = Mock(return_value=False)
    ui = AsyncMock()
    ui.ask_question.return_value.button = "no"
    orca = Orchestrator(state_manager=sm, ui=ui)
    await orca.offline_changes_check()
    assert sm.import_files.assert_not_called
    assert sm.restore_files.assert_called_once


@pytest.mark.asyncio
async def test_import_if_new_files(agentcontext):
    sm, _, ui, _ = agentcontext

    state = await sm.commit()

    orca = Orchestrator(state_manager=sm, ui=ui)
    sm.file_system.save("foo.txt", "bar")

    await orca.import_files()

    # This checks that the state was committed and a new one is now current
    assert state != sm.current_state

    assert len(sm.current_state.files) == 1
    assert sm.current_state.files[0].path == "foo.txt"
    assert sm.current_state.files[0].content.content == "bar"


@pytest.mark.asyncio
async def test_import_if_modified_files(agentcontext):
    sm, _, ui, _ = agentcontext

    await sm.commit()
    await sm.save_file("test.txt", "Hello, world!")
    state = await sm.commit()

    orca = Orchestrator(state_manager=sm, ui=ui)
    sm.file_system.save("test.txt", "bar")

    await orca.import_files()

    # This checks that the state was committed and a new one is now current
    assert state != sm.current_state

    assert len(sm.current_state.files) == 1
    assert sm.current_state.files[0].path == "test.txt"
    assert sm.current_state.files[0].content.content == "bar"


@pytest.mark.asyncio
async def test_import_if_deleted_files(agentcontext):
    sm, _, ui, _ = agentcontext

    await sm.commit()
    await sm.save_file("test.txt", "Hello, world!")
    state = await sm.commit()

    orca = Orchestrator(state_manager=sm, ui=ui)
    sm.file_system.remove("test.txt")

    await orca.import_files()

    # This checks that the state was committed and a new one is now current
    assert state != sm.current_state

    assert len(sm.current_state.files) == 0
