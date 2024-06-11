import os
from typing import Callable
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from core.config import DBConfig
from core.db.models import Base
from core.db.session import SessionManager
from core.state.state_manager import StateManager


@pytest.fixture(autouse=True)
def disable_test_telemetry(monkeypatch):
    os.environ["DISABLE_TELEMETRY"] = "1"


@pytest_asyncio.fixture
async def testmanager():
    """
    Set up a temporary in-memory database for testing.

    This fixture is an async context manager.
    """
    db_cfg = DBConfig(url="sqlite+aiosqlite:///:memory:")
    manager = SessionManager(db_cfg)
    async with manager.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield manager


@pytest_asyncio.fixture
async def testdb(testmanager):
    """
    Set up a temporary in-memory database for testing.

    This fixture is an async context manager that yields
    a database session.
    """
    async with testmanager as db:
        yield db


@pytest_asyncio.fixture
async def agentcontext(testmanager):
    """
    Set up state manager, process manager, UI mock, and LLM mock for testing.

    Database and filesystem are in-memory.

    Yields the (state manager, process manager, UI mock, LLM mock) tuple.
    """
    with patch("core.state.state_manager.get_config") as mock_get_config:
        mock_get_config.return_value.fs.type = "memory"
        sm = StateManager(testmanager)
        pm = MagicMock()
        ui = MagicMock(
            send_project_stage=AsyncMock(),
            send_message=AsyncMock(),
            ask_question=AsyncMock(),
        )

        await sm.create_project("test")

        mock_llm = None

        def mock_get_llm(return_value=None, side_effect=None) -> Callable:
            """
            Returns a function that when called returns an async function
            that when awaited returns the given value, simulatng a LLM call.

            The mock LLM is created only once and reused for all calls in the test.

            :param return_value: The value to return when awaited (optional).
            :param side_effect: The side effect to apply when awaited (optional).
            :return: A function that returns the mocked LLM.
            """
            nonlocal mock_llm

            if not mock_llm:
                mock_llm = MagicMock(  # agent's get_llm() function
                    return_value=AsyncMock(  # the llm() async function
                        return_value=return_value,
                        side_effect=side_effect,
                    )
                )
            return mock_llm

        yield sm, pm, ui, mock_get_llm
