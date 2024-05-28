import datetime
from typing import Optional

import tiktoken
from groq import AsyncGroq, RateLimitError
from httpx import Timeout

from core.config import LLMProvider
from core.llm.base import BaseLLMClient
from core.llm.convo import Convo
from core.log import get_logger

log = get_logger(__name__)
tokenizer = tiktoken.get_encoding("cl100k_base")


class GroqClient(BaseLLMClient):
    provider = LLMProvider.GROQ

    def _init_client(self):
        self.client = AsyncGroq(
            api_key=self.config.api_key,
            base_url=self.config.base_url,
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
        completion_kwargs = {
            "model": self.config.model,
            "messages": convo.messages,
            "temperature": self.config.temperature if temperature is None else temperature,
            "stream": True,
        }
        if json_mode:
            completion_kwargs["response_format"] = {"type": "json_object"}

        stream = await self.client.chat.completions.create(**completion_kwargs)
        response = []
        prompt_tokens = 0
        completion_tokens = 0

        async for chunk in stream:
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
            # FIXME: Here we estimate Groq tokens using the same method as for OpenAI....
            # See https://cookbook.openai.com/examples/how_to_count_tokens_with_tiktoken
            prompt_tokens = sum(3 + len(tokenizer.encode(msg["content"])) for msg in convo.messages)
            completion_tokens = len(tokenizer.encode(response_str))

        return response_str, prompt_tokens, completion_tokens

    def rate_limit_sleep(self, err: RateLimitError) -> Optional[datetime.timedelta]:
        """
        Groq rate limits docs: https://console.groq.com/docs/rate-limits

        Groq includes `retry-after` header when 429 RateLimitError is
        thrown, so we use that instead of calculating our own backoff time.
        """

        headers = err.response.headers
        if "retry-after" not in headers:
            return None

        retry_after = int(err.response.headers["retry-after"])
        return datetime.timedelta(seconds=retry_after)


__all__ = ["GroqClient"]
