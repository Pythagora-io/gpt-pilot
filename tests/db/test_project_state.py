import pytest
from sqlalchemy import select

from core.db.models import Branch, File, FileContent, Project, ProjectState
from core.db.models.project_state import IterationStatus

from .factories import create_project_state


@pytest.mark.asyncio
async def test_get_by_id(testdb):
    state = create_project_state()
    testdb.add(state)
    await testdb.commit()

    s = (await testdb.execute(select(ProjectState).where(ProjectState.id == state.id))).scalar_one_or_none()
    assert s.branch == state.branch
    assert s.branch.project == state.branch.project


@pytest.mark.asyncio
async def test_get_last_state_no_session():
    project = Project(name="test")
    branch = Branch(project=project)

    with pytest.raises(ValueError):
        await branch.get_last_state()


@pytest.mark.asyncio
async def test_get_by_id_preloads_branch_project_files(testdb):
    f = File(path="test.txt", content=FileContent(id="test", content="hello world"))

    state = create_project_state()
    state.files.append(f)
    testdb.add(state)

    await testdb.commit()
    testdb.expunge_all()

    s = (await testdb.execute(select(ProjectState).where(ProjectState.id == state.id))).scalar_one_or_none()

    # If "get_by_id" doesn't populate branch and project and load the files,
    # this will crash because they can't be lazy-loaded without an await.
    assert s.branch.id == state.branch.id
    assert s.branch.project.id == state.branch.project.id
    assert s.files[0].content.content == "hello world"


@pytest.mark.asyncio
async def test_create_next_state_clones_files(testdb):
    f = File(path="test.txt", content=FileContent(id="test", content="hello world"))

    state = create_project_state()
    state.files.append(f)
    testdb.add(state)

    await testdb.commit()

    next_state = await state.create_next_state()

    # Check that the new state has a new file with the same content
    assert next_state.files[0].id != state.files[0].id
    assert next_state.files[0].content_id == f.content_id


@pytest.mark.asyncio
async def test_create_next_deep_copies_fields(testdb):
    state = create_project_state()
    testdb.add(state)

    state.epics = [{"name": "Initial project", "completed": False}]
    state.tasks = [{"description": "test task", "completed": False}]
    state.iterations = [{"description": "test iteration", "completed": False}]
    state.steps = [{"type": "test step", "completed": False}]
    await testdb.commit()

    next_state = await state.create_next_state()

    next_state.epics[0]["completed"] = True
    next_state.tasks[0]["completed"] = True
    next_state.iterations[0]["completed"] = True
    next_state.steps[0]["completed"] = True
    next_state.relevant_files = ["test.txt"]
    next_state.modified_files["test.txt"] = "Hello World"

    assert state.epics[0]["completed"] is False
    assert state.tasks[0]["completed"] is False
    assert state.iterations[0]["completed"] is False
    assert state.steps[0]["completed"] is False
    assert state.relevant_files is None
    assert state.modified_files == {}


@pytest.mark.asyncio
async def test_deleting_state_removes_child_objects(testdb):
    file = File(path="test.txt", content=FileContent(id="test", content="hello world"))

    state = create_project_state()
    testdb.add(state)
    await testdb.commit()

    next_state = await state.create_next_state()
    next_state.files.append(file)
    await testdb.commit()

    # Double-check that objects are in the database
    s = (await testdb.execute(select(ProjectState).where(ProjectState.id == next_state.id))).scalar_one_or_none()
    assert s == next_state
    f = (await testdb.execute(select(File).where(File.id == file.id))).scalar_one_or_none()
    assert f == file

    await state.delete_after()

    # Verify they're deleted
    s = (await testdb.execute(select(ProjectState).where(ProjectState.id == next_state.id))).scalar_one_or_none()
    assert s is None
    f = (await testdb.execute(select(File).where(File.id == file.id))).scalar_one_or_none()
    assert f is None


@pytest.mark.asyncio
async def test_completing_unfinished_steps(testdb):
    state = create_project_state()
    state.steps = [
        {
            "id": "abc",
            "completed": False,
            "type": "create_readme",
        },
    ]
    testdb.add(state)
    await testdb.commit()

    assert state.unfinished_steps == state.steps
    assert state.current_step["id"] == "abc"
    state.complete_step("create_readme")
    assert state.unfinished_steps == []
    assert state.current_step is None
    await testdb.commit()

    await testdb.refresh(state)

    assert state.current_step is None


@pytest.mark.asyncio
async def test_completing_unfinished_iterations(testdb):
    state = create_project_state()
    state.iterations = [
        {
            "id": "abc",
            "description": "LLM breakdown of the iteration",
            "status": IterationStatus.HUNTING_FOR_BUG,
        }
    ]
    testdb.add(state)
    await testdb.commit()

    assert state.unfinished_iterations == state.iterations
    assert state.current_iteration["id"] == "abc"
    state.complete_iteration()
    assert state.unfinished_iterations == []
    assert state.current_iteration is None
    await testdb.commit()

    await testdb.refresh(state)

    assert state.current_iteration is None


@pytest.mark.asyncio
async def test_completing_unfinished_tasks(testdb):
    state = create_project_state()
    state.tasks = [
        {
            "id": "abc",
            "description": "test task",
            "instructions": None,
            "status": "todo",
        }
    ]
    testdb.add(state)
    await testdb.commit()

    assert state.unfinished_tasks == state.tasks
    assert state.current_task["id"] == "abc"
    state.complete_task()
    assert state.unfinished_tasks == []
    assert state.current_task is None
    await testdb.commit()

    await testdb.refresh(state)

    assert state.current_task is None


@pytest.mark.asyncio
async def test_completing_unfinished_epics(testdb):
    state = create_project_state()
    state.epics = [
        {
            "id": "abc",
            "name": "Initial project",
            "description": "Hello World",
            "completed": False,
        }
    ]
    testdb.add(state)
    await testdb.commit()

    assert state.unfinished_epics == state.epics
    assert state.current_epic["id"] == "abc"
    state.complete_epic()
    assert state.unfinished_epics == []
    assert state.current_epic is None
    await testdb.commit()

    await testdb.refresh(state)

    assert state.current_epic is None
