from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field


class ExecLog(BaseModel):
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    duration: float = Field(description="The duration of the command/process run in seconds")
    cmd: str = Field(description="The full command (as executed in the shell)")
    cwd: str = Field(description="The working directory for the command (relative to project root)")
    env: dict = Field(description="The environment variables for the command")
    timeout: Optional[float] = Field(description="The command timeout in seconds (or None if no timeout)")
    status_code: Optional[int] = Field(description="The command return code, or None if there was a timeout")
    stdout: str = Field(description="The command standard output")
    stderr: str = Field(description="The command standard error")
    analysis: str = Field(description="The result analysis as performed by the LLM")
    success: bool = Field(description="Whether the command was successful")


__all__ = ["ExecLog"]
