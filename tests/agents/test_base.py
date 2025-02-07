from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.agents.base import BaseAgent
from core.ui.base import UIBase


class AgentUnderTest(BaseAgent):
    agent_type = "test-agent"
    display_name = "Test Agent"


@pytest.mark.asyncio
async def test_send_message():
    ui = MagicMock(spec=UIBase)
    sm = AsyncMock()
    agent = AgentUnderTest(sm, ui)

    await agent.send_message("Hello, world!")
    ui.send_message.assert_called_once_with(
        "Hello, world!\n",
        source=agent.ui_source,
        project_state_id=str(agent.current_state.id),
        extra_info=None,
    )


@pytest.mark.asyncio
async def test_stream_handler():
    ui = MagicMock(spec=UIBase)
    sm = AsyncMock()
    agent = AgentUnderTest(sm, ui)

    await agent.stream_handler("chunk")
    ui.send_stream_chunk.assert_called_once_with(
        "chunk", source=agent.ui_source, project_state_id=str(agent.current_state.id)
    )


@pytest.mark.asyncio
async def test_ask_question():
    ui = MagicMock()
    state_manager = MagicMock(log_user_input=AsyncMock())
    agent = AgentUnderTest(state_manager, ui)
    ui.ask_question = AsyncMock(return_value="response")

    await agent.ask_question("How are you?", buttons={"ok": "Okay"})
    ui.ask_question.assert_called_once_with(
        "How are you?",
        buttons={"ok": "Okay"},
        buttons_only=False,
        default=None,
        allow_empty=False,
        hint=None,
        verbose=True,
        initial_text=None,
        source=agent.ui_source,
        project_state_id=str(agent.current_state.id),
        full_screen=False,
        extra_info=None,
        placeholder=None,
    )

    state_manager.log_user_input.assert_awaited_once()
    state_manager.log_user_input.assert_called_once_with("How are you?", "response")


@pytest.mark.asyncio
@patch("core.agents.base.BaseLLMClient")
async def test_get_llm(mock_BaseLLMClient):
    ui = MagicMock(spec=UIBase)
    state_manager = MagicMock(log_llm_request=AsyncMock())
    agent = AgentUnderTest(state_manager, ui)
    mock_OpenAIClient = mock_BaseLLMClient.for_provider.return_value

    mock_client = AsyncMock(return_value=("response", "log"))
    mock_OpenAIClient.return_value = mock_client

    llm = agent.get_llm(stream_output=True)

    mock_BaseLLMClient.for_provider.assert_called_once_with("openai")

    mock_OpenAIClient.assert_called_once()
    assert mock_OpenAIClient.call_args.kwargs["stream_handler"] == agent.stream_handler

    response = await llm(None)
    mock_OpenAIClient.return_value.assert_awaited_once_with(None)
    assert response == "response"

    state_manager.log_llm_request.assert_awaited_once()
    assert state_manager.log_llm_request.call_args.args[0] == "log"
