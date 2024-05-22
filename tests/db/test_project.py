from uuid import uuid4

import pytest

from core.db.models import Branch, Project

from .factories import create_project_state


@pytest.mark.asyncio
async def test_get_by_id_requires_valid_uuid(testdb):
    with pytest.raises(ValueError):
        await Project.get_by_id(testdb, "invalid-uuid")


@pytest.mark.asyncio
async def test_get_by_id_no_match(testdb):
    fake_id = uuid4().hex
    result = await Project.get_by_id(testdb, fake_id)
    assert result is None


@pytest.mark.asyncio
async def test_get_by_id(testdb):
    project = Project(name="test")
    testdb.add(project)
    await testdb.commit()

    p = await Project.get_by_id(testdb, project.id)
    assert p == project


@pytest.mark.asyncio
async def test_delete_by_id(testdb):
    project = Project(name="test")
    testdb.add(project)
    await testdb.commit()

    await Project.delete_by_id(testdb, project.id)
    await testdb.commit()
    assert await Project.get_by_id(testdb, project.id) is None


@pytest.mark.asyncio
async def test_get_branch_no_match(testdb):
    project = Project(name="test")
    testdb.add(project)
    await testdb.commit()

    b = await project.get_branch()
    assert b is None


@pytest.mark.asyncio
async def test_get_branch(testdb):
    project = Project(name="test")
    branch = Branch(project=project)
    testdb.add(project)
    testdb.add(branch)
    await testdb.commit()

    b = await project.get_branch()
    assert b == branch


@pytest.mark.asyncio
async def test_get_branch_no_session():
    project = Project(name="test")

    with pytest.raises(ValueError):
        await project.get_branch()


@pytest.mark.asyncio
async def test_get_all_projects(testdb):
    state1 = create_project_state()
    state2 = create_project_state()
    testdb.add(state1)
    testdb.add(state2)

    projects = await Project.get_all_projects(testdb)
    assert len(projects) == 2
    assert state1.branch.project in projects
    assert state2.branch.project in projects


@pytest.mark.asyncio
async def test_default_folder_name(testdb):
    project = Project(name="test project")
    testdb.add(project)
    await testdb.commit()

    assert project.folder_name == "test-project"


@pytest.mark.parametrize(
    ("project_name", "expected_folder_name"),
    [
        ("Test", "test"),
        ("with space", "with-space"),
        ("with   many   spaces", "with-many-spaces"),
        ("w00t? with,interpunction!", "w00t-with-interpunction"),
        ("With special / * and ☺️ emojis", "with-special-and-emojis"),
        ("Šašavi niño & mädchen", "sasavi-nino-madchen"),
    ],
)
def test_get_folder_from_project_name(project_name, expected_folder_name):
    folder_name = Project.get_folder_from_project_name(project_name)
    assert folder_name == expected_folder_name
