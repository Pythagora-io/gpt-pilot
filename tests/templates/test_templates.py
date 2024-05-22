from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.state.state_manager import StateManager
from core.templates.registry import apply_project_template


@pytest.mark.asyncio
@patch("core.state.state_manager.get_config")
async def test_render_javascript_react(mock_get_config, testmanager):
    mock_get_config.return_value.fs.type = "memory"
    sm = StateManager(testmanager)
    pm = MagicMock(run_command=AsyncMock())

    await sm.create_project("TestProjectName")
    await sm.commit()

    summary = await apply_project_template("javascript_react", sm, pm)
    sm.next_state.specification.description = summary
    await sm.commit()

    files = [f.path for f in sm.current_state.files]
    assert "React" in sm.current_state.specification.description
    assert "package.json" in files

    package_json = await sm.get_file_by_path("package.json")
    assert package_json is not None
    assert "TestProjectName" in package_json.content.content

    pm.run_command.assert_awaited_once_with("npm install")


@pytest.mark.asyncio
@patch("core.state.state_manager.get_config")
async def test_render_node_express_mongoose(mock_get_config, testmanager):
    mock_get_config.return_value.fs.type = "memory"
    sm = StateManager(testmanager)
    pm = MagicMock(run_command=AsyncMock())

    await sm.create_project("TestProjectName")
    await sm.commit()

    summary = await apply_project_template("node_express_mongoose", sm, pm)
    sm.next_state.specification.description = summary
    await sm.commit()

    files = [f.path for f in sm.current_state.files]
    assert "Mongoose" in sm.current_state.specification.description
    assert "server.js" in files

    package_json = await sm.get_file_by_path("package.json")
    assert package_json is not None
    assert "TestProjectName" in package_json.content.content

    pm.run_command.assert_awaited_once_with("npm install")
