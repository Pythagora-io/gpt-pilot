from logging import getLogger
from pathlib import Path
import sys
import time
import traceback
from typing import Any
from uuid import uuid4

import requests

from .settings import settings, version, config_path

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
            # Is extension used
            "is_extension": False,
            # LLM used
            "model": None,
            # Initial prompt
            "initial_prompt": None,
            # Number of LLM requests made
            "num_llm_requests": 0,
            # Number of tokens used for LLM requests
            "num_llm_tokens": 0,
            # Number of development steps
            "num_steps": 0,
            # Number of commands run during development
            "num_commands": 0,
            # Number of times a human input was required during development
            "num_inputs": 0,
            # Number of seconds elapsed during development
            "elapsed_time": 0,
            # End result of development ("success", "failure", or None if interrupted)
            "end_result": None,
            # Whether the project is continuation of a previous project
            "is_continuation": False,
            # Optional user feedback
            "user_feedback": None,
            # Optional user contact email
            "user_contact": None,
            # If GPT Pilot crashes, record diagnostics
            "crash_diagnostics": None,
        }
        if sys.platform == "linux":
            try:
                import distro
                self.data["linux_distro"] = distro.name(pretty=True)
            except Exception as err:
                log.debug(f"Error getting Linux distribution info: {err}", exc_info=True)

        self.start_time = None
        self.end_time = None

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

        root_dir = Path(__file__).parent.parent.parent
        stack_trace = traceback.format_exc()
        exception_class_name = exception.__class__.__name__
        exception_message = str(exception)

        tb = exception.__traceback__
        frames = []
        while tb is not None:
            frame = tb.tb_frame
            file_path = Path(frame.f_code.co_filename).absolute().relative_to(root_dir).as_posix()
            frame_info = {
                "file": file_path,
                "line": tb.tb_lineno
            }
            frames.append(frame_info)
            tb = tb.tb_next

        frames.reverse()
        self.data["crash_diagnostics"] = {
            "stack_trace": stack_trace,
            "exception_class": exception_class_name,
            "exception_message": exception_message,
            "frames": frames[:self.MAX_CRASH_FRAMES],
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
        except Exception as e:
            log.error(
                f"Telemetry.send(): failed to send telemetry data: {e}", exc_info=True
            )
        finally:
            self.clear_data()


telemetry = Telemetry()
