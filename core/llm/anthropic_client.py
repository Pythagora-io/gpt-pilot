import asyncio
import datetime
import zoneinfo
from typing import Optional, Tuple

from anthropic import AsyncAnthropic, RateLimitError
from httpx import Timeout

from core.config import LLMProvider
from core.llm.convo import Convo
from core.log import get_logger

from .base import BaseLLMClient

log = get_logger(__name__)

# Maximum number of tokens supported by Anthropic Claude 3
MAX_TOKENS = 4096
MAX_TOKENS_SONNET = 8192


class CustomAssertionError(Exception):
    pass


class AnthropicClient(BaseLLMClient):
    provider = LLMProvider.ANTHROPIC

    def _init_client(self):
        self.client = AsyncAnthropic(
            api_key=self.config.api_key,
            base_url=self.config.base_url,
            timeout=Timeout(
                max(self.config.connect_timeout, self.config.read_timeout),
                connect=self.config.connect_timeout,
                read=self.config.read_timeout,
            ),
        )
        self.stream_handler = self.stream_handler

    def _adapt_messages(self, convo: Convo) -> list[dict[str, str]]:
        """
        Adapt the conversation messages to the format expected by the Anthropic Claude model.

        Claude only recognizes "user" and "assistant" roles, and requires them to be switched
        for each message (i.e. no consecutive messages from the same role).

        :param convo: Conversation to adapt.
        :return: Adapted conversation messages.
        """
        messages = []
        for msg in convo.messages:
            if msg["role"] == "function":
                raise ValueError("Anthropic Claude doesn't support function calling")

            role = "user" if msg["role"] in ["user", "system"] else "assistant"
            if messages and messages[-1]["role"] == role:
                messages[-1]["content"] += "\n\n" + msg["content"]
            else:
                messages.append(
                    {
                        "role": role,
                        "content": msg["content"],
                    }
                )
        return messages

    async def _make_request(
        self, convo: Convo, temperature: Optional[float] = None, json_mode: bool = False, retry_count: int = 1
    ) -> Tuple[str, int, int]:
        async def single_attempt() -> Tuple[str, int, int]:
            messages = self._adapt_messages(convo)
            completion_kwargs = {
                "max_tokens": MAX_TOKENS,
                "model": self.config.model,
                "messages": messages,
                "temperature": self.config.temperature if temperature is None else temperature,
            }

            if "trybricks" in self.config.base_url:
                completion_kwargs["extra_headers"] = {"x-request-timeout": f"{int(float(self.config.read_timeout))}s"}

            if "bedrock/anthropic" in self.config.base_url:
                completion_kwargs["extra_headers"] = {"anthropic-version": "bedrock-2023-05-31"}

            if "sonnet" in self.config.model:
                completion_kwargs["max_tokens"] = MAX_TOKENS_SONNET

            if json_mode:
                completion_kwargs["response_format"] = {"type": "json_object"}

            response = []
            async with self.client.messages.stream(**completion_kwargs) as stream:
                async for content in stream.text_stream:
                    response.append(content)
                    if self.stream_handler:
                        await self.stream_handler(content)

                try:
                    final_message = await stream.get_final_message()
                    final_message.content  # Access content to verify it exists
                except AssertionError:
                    log.debug("Anthropic package AssertionError")
                    raise CustomAssertionError("No final message received.")

            response_str = "".join(response)

            # Tell the stream handler we're done
            if self.stream_handler:
                await self.stream_handler(None)

            return response_str, final_message.usage.input_tokens, final_message.usage.output_tokens

        for attempt in range(retry_count + 1):
            try:
                return await single_attempt()
            except CustomAssertionError as e:
                if attempt == retry_count:  # If this was our last attempt
                    raise CustomAssertionError(f"Request failed after {retry_count + 1} attempts: {str(e)}")
                # Add a small delay before retrying
                await asyncio.sleep(1)
                continue

    def rate_limit_sleep(self, err: RateLimitError) -> Optional[datetime.timedelta]:
        """
        Anthropic rate limits docs:
        https://docs.anthropic.com/en/api/rate-limits#response-headers
        Limit reset times are in RFC 3339 format.
        """
        headers = err.response.headers
        
        # Check if we have the required rate limit headers
        if "anthropic-ratelimit-tokens-remaining" not in headers:
            log.debug("Missing anthropic-ratelimit-tokens-remaining header, falling back to base implementation")
            return super().rate_limit_sleep(err)

        try:
            remaining_tokens = int(headers["anthropic-ratelimit-tokens-remaining"])
        except (ValueError, TypeError):
            log.warning("Invalid anthropic-ratelimit-tokens-remaining value, falling back")
            return super().rate_limit_sleep(err)

        # Determine which reset header to use based on token availability
        reset_header = "anthropic-ratelimit-tokens-reset" if remaining_tokens == 0 else "anthropic-ratelimit-requests-reset"
        
        if reset_header not in headers:
            log.debug(f"Missing {reset_header} header, falling back to base implementation")
            return super().rate_limit_sleep(err)

        reset_time_str = headers[reset_header]

        try:
            # Parse RFC 3339 timestamp with improved error handling
            # Handle both 'Z' suffix and explicit timezone offsets
            if reset_time_str.endswith('Z'):
                reset_time_str = reset_time_str[:-1] + '+00:00'
            
            reset_time = datetime.datetime.fromisoformat(reset_time_str)
            
            # Ensure timezone-aware datetime
            if reset_time.tzinfo is None:
                reset_time = reset_time.replace(tzinfo=datetime.timezone.utc)
                log.debug("Added UTC timezone to naive reset time")
                
        except (ValueError, TypeError) as e:
            log.warning(f"Error parsing Anthropic reset time '{reset_time_str}': {e}, falling back")
            return super().rate_limit_sleep(err)

        # Get current UTC time with better timezone handling
        try:
            now = datetime.datetime.now(tz=zoneinfo.ZoneInfo("UTC"))
        except zoneinfo.ZoneInfoNotFoundError:
            now = datetime.datetime.now(tz=datetime.timezone.utc)

        # Calculate wait duration
        wait_duration = reset_time - now
        wait_seconds = wait_duration.total_seconds()

        # Apply safety bounds
        if wait_seconds < 0:
            log.debug(f"Rate limit reset time is in the past ({wait_seconds:.1f}s ago), using minimal wait")
            return datetime.timedelta(seconds=1)
            
        if wait_seconds > 3600:  # More than 1 hour
            log.warning(f"Rate limit reset time too far in future ({wait_seconds:.1f}s), capping at 1 hour")
            return datetime.timedelta(seconds=3600)

        log.debug(f"Anthropic rate limit: waiting {wait_seconds:.1f}s until {reset_time}")
        return wait_duration


__all__ = ["AnthropicClient"]
