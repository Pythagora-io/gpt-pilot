import asyncio
import datetime
import json
import sys
from enum import Enum
from time import time
from typing import Any, Callable, Optional, Tuple

import httpx
import tiktoken
from httpx import AsyncClient

from core.config import LLMConfig, LLMProvider
from core.llm.convo import Convo
from core.llm.request_log import LLMRequestLog, LLMRequestStatus
from core.log import get_logger
from core.state.state_manager import StateManager
from core.ui.base import UIBase, pythagora_source
from core.utils.text import trim_logs

log = get_logger(__name__)
tokenizer = tiktoken.get_encoding("cl100k_base")


class LLMError(str, Enum):
    KEY_EXPIRED = "key_expired"
    RATE_LIMITED = "rate_limited"
    GENERIC_API_ERROR = "generic_api_error"


class APIError(Exception):
    def __init__(self, message: str):
        self.message = message


class BaseLLMClient:
    """
    Base asynchronous streaming client for language models.

    Example usage:

    >>> async def stream_handler(content: str):
    ...     print(content)
    ...
    >>> def parser(content: str) -> dict:
    ...     return json.loads(content)
    ...
    >>> client_class = BaseClient.for_provider(provider)
    >>> client = client_class(config, stream_handler=stream_handler)
    >>> response, request_log = await client(convo, parser=parser)
    """

    provider: LLMProvider

    def __init__(
        self,
        config: LLMConfig,
        state_manager: StateManager,
        *,
        stream_handler: Optional[Callable] = None,
        error_handler: Optional[Callable] = None,
        ui: Optional[UIBase] = None,
    ):
        """
        Initialize the client with the given configuration.

        :param config: Configuration for the client.
        :param stream_handler: Optional handler for streamed responses.
        """
        self.config = config
        self.stream_handler = stream_handler
        self.error_handler = error_handler
        self.ui = ui
        self.state_manager = state_manager
        self._init_client()

    def _init_client(self):
        raise NotImplementedError()

    async def _make_request(
        self,
        convo: Convo,
        temperature: Optional[float] = None,
        json_mode: bool = False,
    ) -> tuple[str, int, int]:
        """
        Call the Anthropic Claude model with the given conversation.

        Low-level method that streams the response chunks.
        Use `__call__` instead of this method.

        :param convo: Conversation to send to the LLM.
        :param json_mode: If True, the response is expected to be JSON.
        :return: Tuple containing the full response content, number of input tokens, and number of output tokens.
        """
        raise NotImplementedError()

    async def _adapt_messages(self, convo: Convo) -> list[dict[str, str]]:
        """
        Adapt the conversation messages to the format expected by the LLM.

        Claude only recognizes "user" and "assistant roles"

        :param convo: Conversation to adapt.
        :return: Adapted conversation messages.
        """
        messages = []
        for msg in convo.messages:
            if msg.role == "function":
                raise ValueError("Anthropic Claude doesn't support function calling")

            role = "user" if msg.role in ["user", "system"] else "assistant"
            if messages and messages[-1]["role"] == role:
                messages[-1]["content"] += "\n\n" + msg.content
            else:
                messages.append(
                    {
                        "role": role,
                        "content": msg.content,
                    }
                )
        return messages

    async def __call__(
        self,
        convo: Convo,
        *,
        temperature: Optional[float] = None,
        parser: Optional[Callable] = None,
        max_retries: int = 3,
        json_mode: bool = False,
    ) -> Tuple[Any, LLMRequestLog]:
        """
        Invoke the LLM with the given conversation.

        Stream handler, if provided, should be an async function
        that takes a single argument, the response content (str).
        It will be called for each response chunk.

        Parser, if provided, should be a function that takes the
        response content (str) and returns the parsed response.
        On parse error, the parser should raise a ValueError with
        a descriptive error message that will be sent back to the LLM
        to retry, up to max_retries.

        :param convo: Conversation to send to the LLM.
        :param parser: Optional parser for the response.
        :param max_retries: Maximum number of retries for parsing the response.
        :param json_mode: If True, the response is expected to be JSON.
        :return: Tuple of the (parsed) response and request log entry.
        """
        import anthropic
        import groq
        import openai

        if temperature is None:
            temperature = self.config.temperature

        convo = convo.fork()
        request_log = LLMRequestLog(
            provider=self.provider,
            model=self.config.model,
            temperature=temperature,
            prompts=convo.prompt_log,
        )

        prompt_tokens = sum(3 + len(tokenizer.encode(str(msg.get("content", "")))) for msg in convo.messages)

        index = -1
        if prompt_tokens > 150_000:
            for i, msg in enumerate(reversed(convo.messages)):
                if "Here are the backend logs" in msg["content"] or "Here are the frontend logs" in msg["content"]:
                    index = len(convo.messages) - 1 - i
                    break

            if index != -1:
                for i, msg in enumerate(convo.messages):
                    if i < index:
                        convo.messages[i]["content"] = trim_logs(convo.messages[i]["content"])
                    else:
                        break

        prompt_length_kb = len(json.dumps(convo.messages).encode("utf-8")) / 1024
        log.debug(
            f"Calling {self.provider.value} model {self.config.model} (temp={temperature}), prompt length: {prompt_length_kb:.1f} KB, prompt tokens (approx.): {prompt_tokens:.1f}"
        )

        t0 = time()

        remaining_retries = max_retries
        while True:
            if remaining_retries == 0:
                # We've run out of auto-retries
                if request_log.error:
                    last_error_msg = f"Error connecting to the LLM: {request_log.error}"
                else:
                    last_error_msg = "Error parsing LLM response"

                # If we can, ask the user if they want to keep retrying
                if self.error_handler:
                    should_retry = await self.error_handler(LLMError.GENERIC_API_ERROR, message=last_error_msg)
                    if should_retry:
                        remaining_retries = max_retries
                        continue

                # They don't want to retry (or we can't ask them), raise the last error and stop Pythagora
                raise APIError(last_error_msg)

            remaining_retries -= 1
            request_log.messages = convo.messages[:]
            request_log.response = None
            request_log.status = LLMRequestStatus.SUCCESS
            request_log.error = None
            response = None

            try:
                access_token = self.state_manager.get_access_token()

                if access_token:
                    # Store the original client
                    original_client = self.client

                    # Copy client based on its type
                    if isinstance(original_client, openai.AsyncOpenAI):
                        self.client = openai.AsyncOpenAI(
                            api_key=original_client.api_key,
                            base_url=original_client.base_url,
                            timeout=original_client.timeout,
                            default_headers={
                                "Authorization": f"Bearer {access_token}",
                                "Timeout": str(max(self.config.connect_timeout, self.config.read_timeout)),
                            },
                        )
                    elif isinstance(original_client, anthropic.AsyncAnthropic):
                        # Create new Anthropic client with custom headers
                        self.client = anthropic.AsyncAnthropic(
                            api_key=original_client.api_key,
                            base_url=original_client.base_url,
                            timeout=original_client.timeout,
                            default_headers={
                                "Authorization": f"Bearer {access_token}",
                                "Timeout": str(max(self.config.connect_timeout, self.config.read_timeout)),
                            },
                        )
                    elif isinstance(original_client, AsyncClient):
                        self.client = AsyncClient()
                    else:
                        # Handle other client types or raise exception
                        raise ValueError(f"Unsupported client type: {type(original_client)}")

                response, prompt_tokens, completion_tokens = await self._make_request(
                    convo,
                    temperature=temperature,
                    json_mode=json_mode,
                )
            except (openai.APIConnectionError, anthropic.APIConnectionError, groq.APIConnectionError) as err:
                log.warning(f"API connection error: {err}", exc_info=True)
                request_log.error = str(f"API connection error: {err}")
                request_log.status = LLMRequestStatus.ERROR
                continue
            except httpx.ReadTimeout as err:
                log.warning(f"Read timeout (set to {self.config.read_timeout}s): {err}", exc_info=True)
                request_log.error = str(f"Read timeout: {err}")
                request_log.status = LLMRequestStatus.ERROR
                continue
            except httpx.ReadError as err:
                log.warning(f"Read error: {err}", exc_info=True)
                request_log.error = str(f"Read error: {err}")
                request_log.status = LLMRequestStatus.ERROR
                continue
            except (openai.RateLimitError, anthropic.RateLimitError, groq.RateLimitError) as err:
                log.warning(f"Rate limit error: {err}", exc_info=True)
                request_log.error = str(f"Rate limit error: {err}")
                request_log.status = LLMRequestStatus.ERROR
                wait_time = self.rate_limit_sleep(err)
                if wait_time:
                    message = f"We've hit {self.config.provider.value} rate limit. Sleeping for {wait_time.seconds} seconds..."
                    if self.error_handler:
                        await self.error_handler(LLMError.RATE_LIMITED, message)
                    await asyncio.sleep(wait_time.seconds)
                    continue
                else:
                    # RateLimitError that shouldn't be retried, eg. insufficient funds
                    err_msg = err.response.json().get("error", {}).get("message", "Rate limiting error.")
                    raise APIError(err_msg) from err
            except (openai.NotFoundError, anthropic.NotFoundError, groq.NotFoundError) as err:
                err_msg = err.response.json().get("error", {}).get("message", f"Model not found: {self.config.model}")
                raise APIError(err_msg) from err
            except (openai.AuthenticationError, anthropic.AuthenticationError, groq.AuthenticationError) as err:
                log.warning(f"Key expired: {err}", exc_info=True)
                err_msg = err.response.json().get("error", {}).get("message", "Incorrect API key")
                if "[BricksLLM]" in err_msg:
                    # We only want to show the key expired message if it's from Bricks
                    if self.error_handler:
                        should_retry = await self.error_handler(LLMError.KEY_EXPIRED)
                        if should_retry:
                            continue

                raise APIError(err_msg) from err
            except (openai.APIStatusError, anthropic.APIStatusError, groq.APIStatusError) as err:
                # Token limit exceeded (in original gpt-pilot handled as
                # TokenLimitError) is thrown as 400 (OpenAI, Anthropic) or 413 (Groq).
                # All providers throw an exception that is caught here.
                # OpenAI and Groq return a `code` field in the error JSON that lets
                # us confirm that we've breached the token limit, but Anthropic doesn't,
                # so we can't be certain that's the problem in Anthropic case.
                # Here we try to detect that and tell the user what happened.
                log.info(f"API status error: {err}")
                if getattr(err, "status_code", None) in (401, 403):
                    if self.ui:
                        try:
                            await self.ui.send_message("Token expired")
                            sys.exit(0)
                            # TODO implement this to not crash in parallel
                            # access_token = await self.ui.send_token_expired()
                            # self.state_manager.update_access_token(access_token)
                            # continue
                        except Exception:
                            raise APIError("Token expired")

                if getattr(err, "status_code", None) == 400 and getattr(err, "message", None) == "not_enough_tokens":
                    if self.ui:
                        try:
                            await self.ui.ask_question(
                                "",
                                buttons={},
                                buttons_only=True,
                                extra_info={"not_enough_tokens": True},
                                source=pythagora_source,
                            )
                            sys.exit(0)
                            # TODO implement this to not crash in parallel
                            # user_response = await self.ui.ask_question(
                            #     'Not enough tokens left, please top up your account and press "Continue".',
                            #     buttons={"continue": "Continue", "exit": "Exit"},
                            #     buttons_only=True,
                            #     extra_info={"not_enough_tokens": True},
                            #     source=pythagora_source,
                            # )
                            # if user_response.button == "continue":
                            #     continue
                            # else:
                            #     raise APIError("Not enough tokens left")
                        except Exception:
                            raise APIError("Not enough tokens left")

                try:
                    if hasattr(err, "response"):
                        if err.response.headers.get("Content-Type", "").startswith("application/json"):
                            err_code = err.response.json().get("error", {}).get("code", "")
                        else:
                            err_code = str(err.response.text)
                    elif isinstance(err, str):
                        err_code = err
                    else:
                        err_code = json.dumps(err)
                except Exception as e:
                    err_code = f"Error parsing response: {str(e)}"
                if err_code in ("request_too_large", "context_length_exceeded", "string_above_max_length"):
                    # Handle OpenAI and Groq token limit exceeded
                    # OpenAI will return `string_above_max_length` for prompts more than 1M characters
                    message = "".join(
                        [
                            "We sent too large request to the LLM, resulting in an error. ",
                            "This is usually caused by including framework files in an LLM request. ",
                            "Here's how you can get Pythagora to ignore those extra files: ",
                            "https://bit.ly/faq-token-limit-error",
                        ]
                    )
                    raise APIError(message) from err

                log.warning(f"API error: {err}", exc_info=True)
                request_log.error = str(f"API error: {err}")
                request_log.status = LLMRequestStatus.ERROR
                continue
            except (openai.APIError, anthropic.APIError, groq.APIError) as err:
                # Generic LLM API error
                # Make sure this handler is last in the chain as some of the above
                # errors inherit from these `APIError` classes
                log.warning(f"LLM API error {err}", exc_info=True)
                request_log.error = f"LLM had an error processing our request: {err}"
                request_log.status = LLMRequestStatus.ERROR
                continue

            request_log.response = response

            request_log.prompt_tokens += prompt_tokens
            request_log.completion_tokens += completion_tokens
            if parser:
                try:
                    response = parser(response)
                    break
                except ValueError as err:
                    request_log.error = f"Error parsing response: {err}"
                    request_log.status = LLMRequestStatus.ERROR
                    log.debug(f"Error parsing LLM response: {err}, asking LLM to retry", exc_info=True)
                    if response:
                        convo.assistant(response)
                    else:
                        convo.assistant(".")
                    convo.user(f"Error parsing response: {err}. Please output your response EXACTLY as requested.")
                    continue
            else:
                break

        t1 = time()
        request_log.duration = t1 - t0

        log.debug(
            f"Total {self.provider.value} response time {request_log.duration:.2f}s, {request_log.prompt_tokens} prompt tokens, {request_log.completion_tokens} completion tokens used"
        )

        return response, request_log

    @staticmethod
    def for_provider(provider: LLMProvider) -> type["BaseLLMClient"]:
        """
        Return LLM client for the specified provider.

        :param provider: Provider to return the client for.
        :return: Client class for the specified provider.
        """
        from .anthropic_client import AnthropicClient
        from .azure_client import AzureClient
        from .groq_client import GroqClient
        from .minimax_client import MiniMaxClient
        from .openai_client import OpenAIClient
        from .relace_client import RelaceClient

        if provider == LLMProvider.OPENAI:
            return OpenAIClient
        elif provider == LLMProvider.RELACE:
            return RelaceClient
        elif provider == LLMProvider.ANTHROPIC:
            return AnthropicClient
        elif provider == LLMProvider.GROQ:
            return GroqClient
        elif provider == LLMProvider.AZURE:
            return AzureClient
        elif provider == LLMProvider.MINIMAX:
            return MiniMaxClient
        else:
            raise ValueError(f"Unsupported LLM provider: {provider.value}")

    def rate_limit_sleep(self, err: Exception) -> Optional[datetime.timedelta]:
        """
        Return how long we need to sleep because of rate limiting.

        These are computed from the response headers that each LLM returns.
        For details, check the implementation for the specific LLM. If there
        are no rate limiting headers, we assume that the request should not
        be retried and return None (this will be the case for insufficient
        quota/funds in the account).

        :param err: RateLimitError that was raised by the LLM client.
        :return: optional timedelta to wait before trying again
        """

        raise NotImplementedError()


__all__ = ["BaseLLMClient"]
