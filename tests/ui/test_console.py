from unittest.mock import patch

import pytest

from core.ui.base import AgentSource
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
@patch("builtins.input", return_value="awesome")
async def test_ask_question_simple(mock_input):
    ui = PlainConsoleUI()

    await ui.start()
    input = await ui.ask_question("Hello, how are you?")

    assert input.cancelled is False
    assert input.button is None
    assert input.text == "awesome"

    await ui.stop()

    mock_input.assert_called_once()


@pytest.mark.asyncio
@patch("builtins.input", return_value="yes")
async def test_ask_question_with_buttons(mock_input):
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

    mock_input.assert_called_once()


@pytest.mark.asyncio
@patch("builtins.input", side_effect=KeyboardInterrupt())
async def test_ask_question_interrupted(mock_input):
    ui = PlainConsoleUI()

    await ui.start()
    input = await ui.ask_question("Hello, how are you?")

    assert input.cancelled is True
    assert input.button is None
    assert input.text is None

    await ui.stop()

    mock_input.assert_called_once()
