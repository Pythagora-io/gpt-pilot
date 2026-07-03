from unittest.mock import MagicMock

from core.agents.task_completer import TaskCompleter


def _task_completer(current_task, iterations):
    sm = MagicMock()
    sm.current_state.current_task = current_task
    sm.current_state.iterations = iterations
    return TaskCompleter(sm, MagicMock())


def test_summary_without_debugging_is_a_decision():
    tc = _task_completer({"description": "Add a health endpoint"}, [])
    summary, kind = tc._summarize_task_outcome()
    assert summary == "Task: Add a health endpoint"
    assert kind == "decision"


def test_summary_with_debugging_is_a_bug_fix():
    tc = _task_completer(
        {"description": "Add user signup"},
        [{"user_feedback": "Pydantic validation error on user schema", "description": "Added Optional types"}],
    )
    summary, kind = tc._summarize_task_outcome()
    assert kind == "bug_fix"
    assert "Task: Add user signup" in summary
    assert "Debugging: Pydantic validation error on user schema -> Added Optional types" in summary
