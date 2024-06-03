from unittest.mock import AsyncMock, patch

import pytest

from core.ui.base import AgentSource, UIClosedError
from core.ui.console import PlainConsoleUI


@pytest.mark.asyncio
async def test_send_message(capsys):
    src = AgentSource("Product Owner", "product-owner")
    ui = PlainConsoleUI()

    connected = await ui.start()
    assert connected is True
    await ui.send_message("Hello from the other side ♫", source=src)

    captured = capsys.readouterr()
    assert captured.out == "[Product Owner] Hello from the other side ♫\n"
    await ui.stop()


@pytest.mark.asyncio
async def test_stream(capsys):
    src = AgentSource("Product Owner", "product-owner")
    ui = PlainConsoleUI()

    await ui.start()
    for word in ["Hellø ", "fröm ", "the ", "other ", "šide ", "♫"]:
        await ui.send_stream_chunk(word, source=src)

    captured = capsys.readouterr()
    assert captured.out == "Hellø fröm the other šide ♫"
    await ui.stop()


@pytest.mark.asyncio
@patch("core.ui.console.PromptSession")
async def test_ask_question_simple(mock_PromptSession):
    prompt_async = mock_PromptSession.return_value.prompt_async = AsyncMock(return_value="awesome")
    ui = PlainConsoleUI()

    await ui.start()
    input = await ui.ask_question("Hello, how are you?")

    assert input.cancelled is False
    assert input.button is None
    assert input.text == "awesome"

    await ui.stop()

    prompt_async.assert_awaited_once()


@pytest.mark.asyncio
@patch("core.ui.console.PromptSession")
async def test_ask_question_with_buttons(mock_PromptSession):
    prompt_async = mock_PromptSession.return_value.prompt_async = AsyncMock(return_value="yes")
    ui = PlainConsoleUI()

    await ui.start()
    input = await ui.ask_question(
        "Are you sure?",
        buttons={"yes": "Yes, I'm sure", "no": "No, cancel"},
    )

    assert input.cancelled is False
    assert input.button == "yes"
    assert input.text is None

    await ui.stop()

    prompt_async.assert_awaited_once()


@pytest.mark.asyncio
@patch("core.ui.console.PromptSession")
async def test_ask_question_interrupted(mock_PromptSession):
    prompt_async = mock_PromptSession.return_value.prompt_async = AsyncMock(side_effect=KeyboardInterrupt)
    ui = PlainConsoleUI()

    await ui.start()
    with pytest.raises(UIClosedError):
        await ui.ask_question("Hello, how are you?")

    await ui.stop()

    prompt_async.assert_awaited_once()
