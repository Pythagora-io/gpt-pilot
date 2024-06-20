from os import getenv, makedirs
from os.path import join
from sys import platform
from unittest.mock import patch

import pytest
from psutil import Process

from core.proc.process_manager import LocalProcess, ProcessManager


@pytest.mark.skip
@pytest.mark.asyncio
async def test_local_process_start_terminate(tmp_path):
    cmd = "timeout 5" if platform == "win32" else "sleep 5"

    lp = await LocalProcess.start(
        cmd,
        cwd=tmp_path,
        env={"PATH": getenv("PATH")},
        bg=False,
    )

    assert lp.cmd == cmd
    assert lp.cwd == tmp_path
    assert lp.env == {"PATH": getenv("PATH")}
    assert lp.stdout == ""
    assert lp.stderr == ""

    p = Process(lp.pid)
    assert p.is_running()

    await lp.terminate()

    assert not p.is_running()


@pytest.mark.asyncio
async def test_local_process_wait(tmp_path):
    cmd = "timeout 5" if platform == "win32" else "sleep 5"

    lp = await LocalProcess.start(
        cmd,
        cwd=tmp_path,
        env={"PATH": getenv("PATH")},
        bg=False,
    )

    p = Process(lp.pid)
    assert p.is_running()

    await lp.wait(0.1)
    assert not p.is_running()


@pytest.mark.asyncio
@patch("core.proc.process_manager.WATCHER_IDLE_INTERVAL", 0.1)
async def test_process_manager_run_command_capture_stdout(tmp_path):
    pm = ProcessManager(root_dir=tmp_path)

    assert pm.processes == {}

    return_code, stdout, stderr = await pm.run_command("echo hello")

    await pm.stop_watcher()

    assert pm.processes == {}
    assert return_code == 0
    assert stdout.strip() == "hello"
    assert stderr == ""


@pytest.mark.asyncio
@patch("core.proc.process_manager.WATCHER_IDLE_INTERVAL", 0.1)
async def test_process_manager_run_command_capture_stderr(tmp_path):
    pm = ProcessManager(root_dir=tmp_path)

    assert pm.processes == {}

    return_code, stdout, stderr = await pm.run_command("echo hello >&2")

    await pm.stop_watcher()

    assert pm.processes == {}
    assert return_code == 0
    assert stdout == ""
    assert stderr.strip() == "hello"


@pytest.mark.asyncio
@patch("core.proc.process_manager.WATCHER_IDLE_INTERVAL", 0.1)
async def test_process_manager_start_list_terminate(tmp_path):
    cmd = "timeout 5" if platform == "win32" else "sleep 5"
    cwd = join("some", "sub", "directory")
    abs_cwd = join(tmp_path, cwd)
    makedirs(abs_cwd, exist_ok=True)

    pm = ProcessManager(root_dir=tmp_path)
    lp = await pm.start_process(cmd, cwd=cwd, bg=True)

    assert lp.id in pm.processes

    running_processes = pm.list_running_processes()
    assert running_processes == [lp]

    p = Process(lp.pid)
    assert p.cwd() == abs_cwd

    await pm.terminate_process(lp.id)

    await pm.stop_watcher()

    assert p.is_running() is False
    assert lp.id not in pm.processes


@pytest.mark.asyncio
@patch("core.proc.process_manager.WATCHER_IDLE_INTERVAL", 0.1)
async def test_watcher(tmp_path):
    stdout = ""
    stderr = ""
    exited = False

    async def output_handler(out, err):
        nonlocal stdout, stderr
        stdout += out
        stderr += err

    async def exit_handler(process):
        nonlocal exited
        exited = True

    pm = ProcessManager(root_dir=tmp_path, output_handler=output_handler, exit_handler=exit_handler)

    lp = await pm.start_process("echo hello", bg=True)
    import asyncio

    for i in range(10):
        await asyncio.sleep(0.1)
        if exited:
            break
    else:
        raise Exception("Process did not exit within 1s")

    assert stdout.strip() == "hello"
    assert stderr == ""
    assert lp.stdout.strip() == "hello"
    assert lp.stderr == ""

    await pm.stop_watcher()
