import pytest

from core.agents.response import ResponseType
from core.agents.tech_lead import DevelopmentPlan, Epic, TechLead
from core.db.models import Complexity
from core.ui.base import UserInput


@pytest.mark.asyncio
async def test_create_initial_epic(agentcontext):
    """
    If there are no epics defined, the TechLead agent should create an initial project epic.
    """
    sm, _, ui, _ = agentcontext

    sm.current_state.specification.complexity = Complexity.SIMPLE
    sm.current_state.epics = [{"name": "Frontend", "completed": True}]

    tl = TechLead(sm, ui)
    response = await tl.run()
    assert response.type == ResponseType.DONE

    await sm.commit()

    assert sm.current_state.epics != []
    assert sm.current_state.epics[1]["name"] == "Initial Project"
    assert sm.current_state.epics[1]["completed"] is False


@pytest.mark.skip(reason="Temporary")
async def test_apply_project_template(agentcontext):
    sm, _, ui, _ = agentcontext

    sm.current_state.specification.templates = {"node_express_mongoose": {}}
    sm.current_state.epics = [{"name": "Initial Project", "sub_epics": []}]

    await sm.commit()

    tl = TechLead(sm, ui)
    response = await tl.run()
    assert response.type == ResponseType.DONE

    await sm.commit()
    assert sm.current_state.files != []


@pytest.mark.asyncio
async def test_ask_for_feature(agentcontext):
    """
    If there are epics and all are completed, the TechLead agent should ask for a new feature.
    """
    sm, _, ui, _ = agentcontext

    sm.current_state.epics = [
        {"name": "Frontend", "completed": True},
        {"name": "Initial Project", "completed": True},
    ]
    ui.ask_question.return_value = UserInput(text="make it pop")

    tl = TechLead(sm, ui)
    response = await tl.run()
    assert response.type == ResponseType.UPDATE_SPECIFICATION

    await sm.commit()

    assert len(sm.current_state.epics) == 3
    assert sm.current_state.epics[2]["description"] == "make it pop"
    assert sm.current_state.epics[2]["completed"] is False


@pytest.mark.skip(reason="Temporary")
async def test_plan_epic(agentcontext):
    """
    If called and there's an incomplete epic, the TechLead agent should plan the epic.
    """
    sm, _, ui, mock_get_llm = agentcontext

    sm.current_state.epics = [
        {
            "id": "abc",
            "name": "Initial Project",
            "description": "hello world",
            "complexity": Complexity.SIMPLE,
            "completed": False,
        }
    ]
    await sm.commit()

    tl = TechLead(sm, ui)
    tl.get_llm = mock_get_llm(
        return_value=DevelopmentPlan(
            plan=[
                Epic(description="Task 1"),
                Epic(description="Task 2"),
            ]
        )
    )
    response = await tl.run()
    assert response.type == ResponseType.DONE

    await sm.commit()

    assert len(sm.current_state.tasks) == 2
    assert sm.current_state.tasks[0]["description"] == "Task 1"
    assert sm.current_state.tasks[1]["description"] == "Task 2"
