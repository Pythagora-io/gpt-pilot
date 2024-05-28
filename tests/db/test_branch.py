from uuid import uuid4

import pytest

from core.db.models import Branch, Project

from .factories import create_project_state


@pytest.mark.asyncio
async def test_get_by_id_requires_valid_uuid(testdb):
    with pytest.raises(ValueError):
        await Branch.get_by_id(testdb, "invalid-uuid")


@pytest.mark.asyncio
async def test_get_by_id_no_match(testdb):
    fake_id = uuid4().hex
    result = await Branch.get_by_id(testdb, fake_id)
    assert result is None


@pytest.mark.asyncio
async def test_get_by_id(testdb):
    project = Project(name="test")
    branch = Branch(project=project)
    testdb.add(project)
    await testdb.commit()

    b = await Branch.get_by_id(testdb, branch.id)
    assert b == branch
    assert b.name == Branch.DEFAULT


@pytest.mark.asyncio
async def test_get_last_state_no_steps(testdb):
    project = Project(name="test")
    branch = Branch(project=project)
    testdb.add(project)
    await testdb.commit()

    s = await branch.get_last_state()
    assert s is None


@pytest.mark.asyncio
async def test_get_last_state(testdb):
    state1 = create_project_state()
    testdb.add(state1)
    await testdb.commit()

    state2 = await state1.create_next_state()
    testdb.add(state2)
    await testdb.commit()

    s = await state1.branch.get_last_state()
    assert s == state2
    assert s.branch == state1.branch
    assert s.branch.project == state1.branch.project


@pytest.mark.asyncio
async def test_get_last_state_no_session():
    project = Project(name="test")
    branch = Branch(project=project)

    with pytest.raises(ValueError):
        await branch.get_last_state()
