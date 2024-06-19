import pytest

from core.agents.troubleshooter import RouteFilePaths, Troubleshooter
from core.db.models import File, FileContent


@pytest.mark.asyncio
async def test_route_files_are_included_in_the_prompt(agentcontext):
    sm, _, ui, mock_get_llm = agentcontext

    sm.current_state.tasks = [{"description": "Some task", "status": "todo", "instructions": "Testing here!"}]
    files = [
        File(path="dir/file1.js", content=FileContent(content="File 1 content")),
        File(path="dir/file2.js", content=FileContent(content="File 2 content")),
    ]

    await sm.commit()
    sm.current_state.files = files

    ts = Troubleshooter(sm, ui)
    ts.get_llm = mock_get_llm(
        side_effect=[
            RouteFilePaths(files=["dir/file1.js"]),  # First LLM call, to select files with routes
            "",  # Second LLM call, to generate the actual instructions
        ]
    )
    await ts.get_user_instructions()
    second_llm_call = ts.get_llm().call_args_list[1]
    user_msg_contents = [msg["content"] for msg in second_llm_call[0][0] if msg["role"] == "user"]
    assert "File 1 content" in user_msg_contents[1]  # Prompt at [1] has the route file contents
    assert "File 2 content" not in user_msg_contents[1]
