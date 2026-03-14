import datetime
import os
import re
from typing import Optional

import tiktoken
from httpx import Timeout
from openai import AsyncOpenAI, RateLimitError

from core.config import LLMProvider
from core.llm.base import BaseLLMClient
from core.llm.convo import Convo
from core.log import get_logger

log = get_logger(__name__)
tokenizer = tiktoken.get_encoding("cl100k_base")

# MiniMax API base URL (international)
MINIMAX_BASE_URL = "https://api.minimax.io/v1"

# MiniMax temperature must be in (0.0, 1.0], cannot be 0
MINIMAX_MIN_TEMPERATURE = 0.01


class MiniMaxClient(BaseLLMClient):
    provider = LLMProvider.MINIMAX

    def _init_client(self):
        api_key = self.config.api_key or os.environ.get("MINIMAX_API_KEY")
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=self.config.base_url or MINIMAX_BASE_URL,
            timeout=Timeout(
                max(self.config.connect_timeout, self.config.read_timeout),
                connect=self.config.connect_timeout,
                read=self.config.read_timeout,
            ),
        )

    async def _make_request(
        self,
        convo: Convo,
        temperature: Optional[float] = None,
        json_mode: bool = False,
    ) -> tuple[str, int, int]:
        temp = self.config.temperature if temperature is None else temperature
        # MiniMax requires temperature > 0
        if temp <= 0:
            temp = MINIMAX_MIN_TEMPERATURE

        completion_kwargs = {
            "model": self.config.model,
            "messages": convo.messages,
            "temperature": temp,
            "stream": True,
        }

        # MiniMax does not support response_format; skip json_mode

        stream = await self.client.chat.completions.create(**completion_kwargs)
        response = []
        prompt_tokens = 0
        completion_tokens = 0

        async for chunk in stream:
            if chunk.usage:
                prompt_tokens += chunk.usage.prompt_tokens
                completion_tokens += chunk.usage.completion_tokens

            if not chunk.choices:
                continue

            content = chunk.choices[0].delta.content
            if not content:
                continue

            response.append(content)
            if self.stream_handler:
                await self.stream_handler(content)

        response_str = "".join(response)

        # Tell the stream handler we're done
        if self.stream_handler:
            await self.stream_handler(None)

        if prompt_tokens == 0 and completion_tokens == 0:
            prompt_tokens = sum(3 + len(tokenizer.encode(msg["content"])) for msg in convo.messages)
            completion_tokens = len(tokenizer.encode(response_str))
            log.warning(
                "MiniMax response did not include token counts, estimating with tiktoken: "
                f"{prompt_tokens} input tokens, {completion_tokens} output tokens"
            )

        return response_str, prompt_tokens, completion_tokens

    def rate_limit_sleep(self, err: RateLimitError) -> Optional[datetime.timedelta]:
        """
        Handle MiniMax rate limiting using OpenAI-compatible headers.
        """
        headers = err.response.headers
        if "x-ratelimit-remaining-tokens" not in headers:
            # Check for retry-after header as fallback
            if "retry-after" in headers:
                return datetime.timedelta(seconds=int(headers["retry-after"]))
            return None

        remaining_tokens = headers["x-ratelimit-remaining-tokens"]
        time_regex = r"(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?"
        if remaining_tokens == 0:
            match = re.search(time_regex, headers.get("x-ratelimit-reset-tokens", ""))
        else:
            match = re.search(time_regex, headers.get("x-ratelimit-reset-requests", ""))

        if match:
            hours = int(match.group(1)) if match.group(1) else 0
            minutes = int(match.group(2)) if match.group(2) else 0
            seconds = int(match.group(3)) if match.group(3) else 0
            total_seconds = hours * 3600 + minutes * 60 + seconds
        else:
            total_seconds = 5

        return datetime.timedelta(seconds=total_seconds)


__all__ = ["MiniMaxClient"]
