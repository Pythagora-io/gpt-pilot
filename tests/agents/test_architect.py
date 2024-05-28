from unittest.mock import AsyncMock

import pytest

from core.agents.architect import Architect, Architecture, PackageDependency, SystemDependency
from core.agents.response import ResponseType
from core.ui.base import UserInput


@pytest.mark.asyncio
async def test_run(agentcontext):
    sm, pm, ui, mock_get_llm = agentcontext

    ui.ask_question.return_value = UserInput(button="continue")
    pm.run_command = AsyncMock(return_value=(0, "", ""))

    arch = Architect(sm, ui, process_manager=pm)
    arch.get_llm = mock_get_llm(
        return_value=Architecture(
            architecture="dummy arch",
            system_dependencies=[
                SystemDependency(
                    name="docker",
                    description="Docker is a containerization platform.",
                    test="docker --version",
                    required_locally=True,
                )
            ],
            package_dependencies=[
                PackageDependency(
                    name="express",
                    description="Express is a Node.js framework.",
                )
            ],
            template="javascript_react",
        )
    )
    response = await arch.run()

    arch.get_llm.return_value.assert_awaited_once()
    ui.ask_question.assert_awaited_once()
    pm.run_command.assert_awaited_once_with("docker --version")

    assert response.type == ResponseType.DONE

    await sm.commit()

    assert sm.current_state.specification.architecture == "dummy arch"
    assert sm.current_state.specification.system_dependencies[0]["name"] == "docker"
    assert sm.current_state.specification.package_dependencies[0]["name"] == "express"
    assert sm.current_state.specification.template == "javascript_react"
