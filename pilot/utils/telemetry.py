from logging import getLogger
from pathlib import Path
import sys
import time
import traceback
from typing import Any
from uuid import uuid4

import requests

from .settings import settings, version, config_path
from const.telemetry import LARGE_REQUEST_THRESHOLD, SLOW_REQUEST_THRESHOLD

log = getLogger(__name__)


class Telemetry:
    """
    Anonymous telemetry.

    See ../../docs/TELEMETRY.md for more information on what is collected
    and how to disable it on a configuration level.

    This class is a singleton, use the `telemetry` global variable to access it:

    >>> from utils.telemetry import telemetry

    To set up telemetry (only once, at GPT-Pilot setup), use the
    `telemetry.setup()` method:

    >>> telemetry.setup()

    To record start of application creation process:

    >>> telemetry.start()

    To record data or increase counters:

    >>> telemetry.set("model", "gpt-4")
    >>> telemetry.inc("num_llm_requests", 5)

    To stop recording and send the data:

    >>> telemetry.stop()
    >>> telemetry.send()

    Note: all methods are no-ops if telemetry is not enabled.
    """

    DEFAULT_ENDPOINT = "https://api.pythagora.io/telemetry"
    MAX_CRASH_FRAMES = 3

    def __init__(self):
        self.enabled = False
        self.telemetry_id = None
        self.endpoint = None
        self.clear_data()

        if settings.telemetry is not None:
            self.enabled = settings.telemetry.get("enabled", False)
            self.telemetry_id = settings.telemetry.get("id")
            self.endpoint = settings.telemetry.get("endpoint")

        if self.enabled:
            log.debug(
                f"Anonymous telemetry enabled (id={self.telemetry_id}), "
                f"configure or disable it in {config_path}"
            )

    def clear_data(self):
        """
        Reset all telemetry data to default values.
        """
        self.data = {
            # System platform
            "platform": sys.platform,
            # Python version used for GPT Pilot
            "python_version": sys.version,
            # GPT Pilot version
            "pilot_version": version,
            # GPT Pilot Extension version
            "extension_version": None,
            # Is extension used
            "is_extension": False,
            # LLM used
            "model": None,
            # Initial prompt
            "initial_prompt": None,
            # Optional user contact email
            "user_contact": None,
            # Unique project ID (app_id)
            "app_id": None,
            # Project architecture
            "architecture": None,
        }
        if sys.platform == "linux":
            try:
                import distro
                self.data["linux_distro"] = distro.name(pretty=True)
            except Exception as err:
                log.debug(f"Error getting Linux distribution info: {err}", exc_info=True)
        self.clear_counters()

    def clear_counters(self):
        """
        Reset telemetry counters while keeping the base data.
        """
        self.data.update({
            # Number of LLM requests made
            "num_llm_requests": 0,
            # Number of LLM requests that resulted in an error
            "num_llm_errors": 0,
            # Number of tokens used for LLM requests
            "num_llm_tokens": 0,
            # Number of development steps
            "num_steps": 0,
            # Number of commands run during development
            "num_commands": 0,
            # Number of times a human input was required during development
            "num_inputs": 0,
            # Number of files in the project
            "num_files": 0,
            # Total number of lines in the project
            "num_lines": 0,
            # Number of tasks started during development
            "num_tasks": 0,
            # Number of seconds elapsed during development
            "elapsed_time": 0,
            # Total number of lines created by GPT Pilot
            "created_lines": 0,
            # End result of development:
            # - success:initial-project
            # - success:feature
            # - success:exit
            # - failure
            # - failure:api-error
            # - interrupt
            "end_result": None,
            # Whether the project is continuation of a previous session
            "is_continuation": False,
            # Optional user feedback
            "user_feedback": None,
            # If GPT Pilot crashes, record diagnostics
            "crash_diagnostics": None,
            # Statistics for large requests
            "large_requests": None,
            # Statistics for slow requests
            "slow_requests": None,
        })
        self.start_time = None
        self.end_time = None
        self.large_requests = []
        self.slow_requests = []

    def setup(self):
        """
        Set up a new unique telemetry ID and default phone-home endpoint.

        This should only be called once at initial GPT-Pilot setup.
        """
        if self.enabled:
            log.debug("Telemetry already set up, not doing anything")
            return

        self.telemetry_id = f"telemetry-{uuid4()}"
        self.endpoint = self.DEFAULT_ENDPOINT
        self.enabled = True
        log.debug(
            f"Telemetry.setup(): setting up anonymous telemetry (id={self.telemetry_id})"
        )

        settings.telemetry = {
            "id": self.telemetry_id,
            "endpoint": self.endpoint,
            "enabled": self.enabled,
        }

    def set(self, name: str, value: Any):
        """
        Set a telemetry data field to a value.

        :param name: name of the telemetry data field
        :param value: value to set the field to

        Note: only known data fields may be set, see `Telemetry.clear_data()` for a list.
        """
        if not self.enabled:
            return

        if name not in self.data:
            log.error(
                f"Telemetry.record(): ignoring unknown telemetry data field: {name}"
            )
            return

        self.data[name] = value

    def inc(self, name: str, value: int = 1):
        """
        Increase a telemetry data field by a value.

        :param name: name of the telemetry data field
        :param value: value to increase the field by (default: 1)

        Note: only known data fields may be increased, see `Telemetry.clear_data()` for a list.
        """
        if not self.enabled:
            return

        if name not in self.data:
            log.error(
                f"Telemetry.increase(): ignoring unknown telemetry data field: {name}"
            )
            return

        self.data[name] += value

    def start(self):
        """
        Record start of application creation process.
        """
        if not self.enabled:
            return

        self.start_time = time.time()
        self.end_time = None

    def stop(self):
        """
        Record end of application creation process.
        """
        if not self.enabled:
            return

        if self.start_time is None:
            log.error("Telemetry.stop(): cannot stop telemetry, it was never started")
            return

        self.end_time = time.time()
        self.data["elapsed_time"] = int(self.end_time - self.start_time)

    def record_crash(
        self,
        exception: Exception,
        end_result: str = "failure",
    ):
        """
        Record crash diagnostics.

        :param error: exception that caused the crash

        Records the following crash diagnostics data:
        * full stack trace
        * exception (class name and message)
        * file:line for the last (innermost) 3 frames of the stack trace
        """
        if not self.enabled:
            return

        self.set("end_result", end_result)

        root_dir = Path(__file__).parent.parent.parent
        stack_trace = traceback.format_exc()
        exception_class_name = exception.__class__.__name__
        exception_message = str(exception)
        frames = []

        # Let's not crash if there's something funny in frame or path handling
        try:
            tb = exception.__traceback__
            while tb is not None:
                frame = tb.tb_frame
                file_path = Path(frame.f_code.co_filename).absolute().relative_to(root_dir).as_posix()
                frame_info = {
                    "file": file_path,
                    "line": tb.tb_lineno
                }
                if not file_path.startswith('pilot-env'):
                    frames.append(frame_info)
                tb = tb.tb_next
        except:  # noqa
            pass

        frames.reverse()
        self.data["crash_diagnostics"] = {
            "stack_trace": stack_trace,
            "exception_class": exception_class_name,
            "exception_message": exception_message,
            "frames": frames[:self.MAX_CRASH_FRAMES],
        }

    def record_llm_request(
        self,
        tokens: int,
        elapsed_time: int,
        is_error: bool,
    ):
        """
        Record an LLM request.

        :param tokens: number of tokens in the request
        :param elapsed_time: time elapsed for the request
        :param is_error: whether the request resulted in an error
        """
        if not self.enabled:
            return

        self.inc("num_llm_requests")

        if is_error:
            self.inc("num_llm_errors")
        else:
            self.inc("num_llm_tokens", tokens)

        if tokens > LARGE_REQUEST_THRESHOLD:
            self.large_requests.append(tokens)
        if elapsed_time > SLOW_REQUEST_THRESHOLD:
            self.slow_requests.append(elapsed_time)

    def calculate_statistics(self):
        """
        Calculate statistics for large and slow requests.
        """
        if not self.enabled:
            return

        n_large = len(self.large_requests)
        n_slow = len(self.slow_requests)

        self.data["large_requests"] = {
            "num_requests": n_large,
            "min_tokens": min(self.large_requests) if n_large > 0 else None,
            "max_tokens": max(self.large_requests) if n_large > 0 else None,
            "avg_tokens": sum(self.large_requests) // n_large if n_large > 0 else None,
            "median_tokens": sorted(self.large_requests)[n_large // 2] if n_large > 0 else None,
        }
        self.data["slow_requests"] = {
            "num_requests": n_slow,
            "min_time": min(self.slow_requests) if n_slow > 0 else None,
            "max_time": max(self.slow_requests) if n_slow > 0 else None,
            "avg_time": sum(self.slow_requests) // n_slow if n_slow > 0 else None,
            "median_time": sorted(self.slow_requests)[n_slow // 2] if n_slow > 0 else None,
        }

    def send(self, event:str = "pilot-telemetry"):
        """
        Send telemetry data to the phone-home endpoint.

        Note: this method clears all telemetry data after sending it.
        """
        if not self.enabled:
            return

        if self.endpoint is None:
            log.error("Telemetry.send(): cannot send telemetry, no endpoint configured")
            return

        if self.start_time is not None and self.end_time is None:
            self.stop()

        self.calculate_statistics()
        payload = {
            "pathId": self.telemetry_id,
            "event": event,
            "data": self.data,
        }

        log.debug(
            f"Telemetry.send(): sending anonymous telemetry data to {self.endpoint}"
        )
        try:
            requests.post(self.endpoint, json=payload)
            self.clear_counters()
            self.set("is_continuation", True)
        except Exception as e:
            log.error(
                f"Telemetry.send(): failed to send telemetry data: {e}", exc_info=True
            )


telemetry = Telemetry()
