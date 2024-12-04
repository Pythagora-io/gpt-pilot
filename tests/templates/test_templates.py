from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.state.state_manager import StateManager
from core.templates.registry import PROJECT_TEMPLATES


@pytest.mark.skip
@pytest.mark.asyncio
@patch("core.state.state_manager.get_config")
async def test_render_react_express_sql(mock_get_config, testmanager):
    mock_get_config.return_value.fs.type = "memory"
    sm = StateManager(testmanager)
    pm = MagicMock(run_command=AsyncMock())

    await sm.create_project("TestProjectName")
    await sm.commit()

    TemplateClass = PROJECT_TEMPLATES["react_express"]
    options = TemplateClass.options_class(db_type="sql", auth=True)
    template = TemplateClass(options, sm, pm)

    assert template.options_dict == {"db_type": "sql", "auth": True}

    await template.apply()

    files = sm.file_system.list()
    for f in ["server.js", "index.html", "prisma/schema.prisma", "api/routes/authRoutes.js", "ui/pages/Register.jsx"]:
        assert f in files
    assert "api/models/user.js" not in files


@pytest.mark.skip
@pytest.mark.asyncio
@patch("core.state.state_manager.get_config")
async def test_render_react_express_nosql(mock_get_config, testmanager):
    mock_get_config.return_value.fs.type = "memory"
    sm = StateManager(testmanager)
    pm = MagicMock(run_command=AsyncMock())

    await sm.create_project("TestProjectName")
    await sm.commit()

    TemplateClass = PROJECT_TEMPLATES["react_express"]
    options = TemplateClass.options_class(db_type="nosql", auth=True)
    template = TemplateClass(options, sm, pm)

    assert template.options_dict == {"db_type": "nosql", "auth": True}

    await template.apply()

    files = sm.file_system.list()
    print(files)
    for f in ["server.js", "index.html", "api/models/user.js", "api/routes/authRoutes.js", "ui/pages/Register.jsx"]:
        assert f in files
    assert "prisma/schema.prisma" not in files


@pytest.mark.skip
@pytest.mark.asyncio
@patch("core.state.state_manager.get_config")
async def test_render_node_express_mongoose(mock_get_config, testmanager):
    mock_get_config.return_value.fs.type = "memory"
    sm = StateManager(testmanager)
    pm = MagicMock(run_command=AsyncMock())

    await sm.create_project("TestProjectName")
    await sm.commit()

    TemplateClass = PROJECT_TEMPLATES["node_express_mongoose"]
    template = TemplateClass(TemplateClass.options_class(), sm, pm)

    assert template.options_dict == {}

    await template.apply()

    files = sm.file_system.list()
    for f in ["server.js", "models/User.js"]:
        assert f in files
