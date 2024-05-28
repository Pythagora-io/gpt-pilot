from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from core.config import LLMProvider


class LLMRequestStatus(str, Enum):
    SUCCESS = "success"
    ERROR = "error"


class LLMRequestLog(BaseModel):
    provider: LLMProvider
    model: str
    temperature: float
    messages: list[dict[str, str]] = Field(default_factory=list)
    prompts: list[dict[str, Any]] = Field(default_factory=list)
    response: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    started_at: datetime = Field(default_factory=datetime.now)
    duration: float = 0.0
    status: LLMRequestStatus = LLMRequestStatus.SUCCESS
    error: str = ""


__all__ = ["LLMRequestLog", "LLMRequestStatus"]
