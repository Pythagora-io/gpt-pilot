import asyncio
import signal
import sys
import time
from copy import deepcopy
from dataclasses import dataclass
from os import environ
from os.path import abspath, join
from typing import Callable, Optional
from uuid import UUID, uuid4

import psutil

from core.log import get_logger

log = get_logger(__name__)

NONBLOCK_READ_TIMEOUT = 0.01
BUSY_WAIT_INTERVAL = 0.1
WATCHER_IDLE_INTERVAL = 1.0
MAX_COMMAND_TIMEOUT = 180


@dataclass
class LocalProcess:
    id: UUID
    cmd: str
    cwd: str
    env: dict[str, str]
    stdout: str
    stderr: str
    _process: asyncio.subprocess.Process

    def __hash__(self) -> int:
        return hash(self.id)

    @staticmethod
    async def start(
        cmd: str,
        *,
        cwd: str = ".",
        env: dict[str, str],
        bg: bool = False,
    ) -> "LocalProcess":
        log.debug(f"Starting process: {cmd} (cwd={cwd})")
        _process = await asyncio.create_subprocess_shell(
            cmd,
            cwd=cwd,
            env=env,
            start_new_session=bg,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        if bg:
            _process.stdin.close()

        return LocalProcess(
            id=uuid4(),
            cmd=cmd,
            cwd=cwd,
            env=env,
            stdout="",
            stderr="",
            _process=_process,
        )

    async def wait(self, timeout: Optional[float] = None) -> int:
        try:
            future = self._process.wait()
            if timeout:
                future = asyncio.wait_for(future, timeout)
            retcode = await future
        except asyncio.TimeoutError:
            log.debug(f"Process {self.cmd} still running after {timeout}s, terminating")
            await self.terminate()
            # FIXME: this may still hang if we don't manage to kill the process.
            retcode = await self._process.wait()

        return retcode

    @staticmethod
    async def _nonblock_read(reader: asyncio.StreamReader, timeout: float) -> str:
        """
        Reads data from a stream reader without blocking (for long).

        This wraps the read in a (short) timeout to avoid blocking the event loop for too long.

        :param reader: Async stream reader to read from.
        :param timeout: Timeout for the read operation (should not be too long).
        :return: Data read from the stream reader, or empty string.
        """
        buffer = ""
        while True:
            try:
                data = await asyncio.wait_for(reader.read(1), timeout)
                if not data:
                    return buffer
                buffer += data.decode("utf-8", errors="ignore")
            except asyncio.TimeoutError:
                return buffer

    async def read_output(self, timeout: float = NONBLOCK_READ_TIMEOUT) -> tuple[str, str]:
        new_stdout = await self._nonblock_read(self._process.stdout, timeout)
        new_stderr = await self._nonblock_read(self._process.stderr, timeout)
        self.stdout += new_stdout
        self.stderr += new_stderr
        return (new_stdout, new_stderr)

    async def _terminate_process_tree(self, signal: int):
        # This is a recursive function that terminates the entire process tree
        # of the current process. It first terminates all child processes, then
        # terminates itself.
        shell_process = psutil.Process(self._process.pid)
        processes = shell_process.children(recursive=True)
        processes.append(shell_process)
        for proc in processes:
            try:
                proc.send_signal(signal)
            except psutil.NoSuchProcess:
                pass

        psutil.wait_procs(processes, timeout=1)

    async def terminate(self, kill: bool = True):
        if kill and sys.platform != "win32":
            await self._terminate_process_tree(signal.SIGKILL)
        else:
            # Windows doesn't have SIGKILL
            await self._terminate_process_tree(signal.SIGTERM)

    @property
    def is_running(self) -> bool:
        try:
            return psutil.Process(self._process.pid).is_running()
        except psutil.NoSuchProcess:
            return False

    @property
    def pid(self) -> int:
        return self._process.pid


class ProcessManager:
    def __init__(
        self,
        *,
        root_dir: str,
        env: Optional[dict[str, str]] = None,
        output_handler: Optional[Callable] = None,
        exit_handler: Optional[Callable] = None,
    ):
        if env is None:
            env = deepcopy(environ)
        self.processes: dict[UUID, LocalProcess] = {}
        self.default_env = env
        self.root_dir = root_dir
        self.watcher_should_run = True
        self.watcher_task = asyncio.create_task(self.watcher())
        self.output_handler = output_handler
        self.exit_handler = exit_handler

    async def stop_watcher(self):
        """
        Stop the process watcher.

        This should only be done when the ProcessManager is no longer needed.
        """
        if not self.watcher_should_run:
            raise ValueError("Process watcher is not running")

        self.watcher_should_run = False
        await self.watcher_task

    async def watcher(self):
        """
        Watch over the processes and manage their output and lifecycle.

        This is a separate coroutine running independently of the caller
        coroutine.
        """
        # IDs of processes whos output has been fully read after they finished
        complete_processes = set()

        while self.watcher_should_run:
            procs = [p for p in self.processes.values() if p.id not in complete_processes]
            if len(procs) == 0:
                await asyncio.sleep(WATCHER_IDLE_INTERVAL)
                continue

            for process in procs:
                out, err = await process.read_output()
                if self.output_handler and (out or err):
                    await self.output_handler(out, err)

                if not process.is_running:
                    # We're not removing the complete process from the self.processes
                    # list to give time to the rest of the system to read its outputs
                    complete_processes.add(process.id)
                    if self.exit_handler:
                        await self.exit_handler(process)

            # Sleep a bit to avoid busy-waiting
            await asyncio.sleep(BUSY_WAIT_INTERVAL)

    async def start_process(
        self,
        cmd: str,
        *,
        cwd: str = ".",
        env: Optional[dict[str, str]] = None,
        bg: bool = True,
    ) -> LocalProcess:
        env = {**self.default_env, **(env or {})}
        abs_cwd = abspath(join(self.root_dir, cwd))
        process = await LocalProcess.start(cmd, cwd=abs_cwd, env=env, bg=bg)
        if bg:
            self.processes[process.id] = process
        return process

    async def run_command(
        self,
        cmd: str,
        *,
        cwd: str = ".",
        env: Optional[dict[str, str]] = None,
        timeout: float = MAX_COMMAND_TIMEOUT,
        show_output: Optional[bool] = True,
    ) -> tuple[Optional[int], str, str]:
        """
        Run command and wait for it to finish.

        Status code is an integer representing the process exit code, or
        None if the process timed out and was terminated.

        :param cmd: Command to run.
        :param cwd: Working directory.
        :param env: Environment variables.
        :param timeout: Timeout in seconds.
        :param show_output: Show output in the ui.
        :return: Tuple of (status code, stdout, stderr).
        """
        timeout = min(timeout, MAX_COMMAND_TIMEOUT)
        terminated = False
        process = await self.start_process(cmd, cwd=cwd, env=env, bg=False)

        t0 = time.time()
        while process.is_running and (time.time() - t0) < timeout:
            out, err = await process.read_output(BUSY_WAIT_INTERVAL)
            if self.output_handler and (out or err) and show_output:
                await self.output_handler(out, err)

        if process.is_running:
            log.debug(f"Process {cmd} still running after {timeout}s, terminating")
            await process.terminate()
            terminated = True
        else:
            await process.wait()

        out, err = await process.read_output()
        if self.output_handler and (out or err) and show_output:
            await self.output_handler(out, err)

        if terminated:
            status_code = None
        else:
            status_code = process._process.returncode or 0

        return (status_code, process.stdout, process.stderr)

    def list_running_processes(self):
        return [p for p in self.processes.values() if p.is_running]

    async def terminate_process(self, process_id: UUID) -> tuple[str, str]:
        if process_id not in self.processes:
            raise ValueError(f"Process {process_id} not found")

        process = self.processes[process_id]
        await process.terminate(kill=False)
        del self.processes[process_id]

        return (process.stdout, process.stderr)
