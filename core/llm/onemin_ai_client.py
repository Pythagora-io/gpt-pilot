import datetime
import re
import requests
from typing import Optional
from core.config import LLMProvider
from core.llm.base import BaseLLMClient
from core.llm.convo import Convo
from core.log import get_logger

log = get_logger(__name__)

class OneMinAIClient(BaseLLMClient):
    provider = LLMProvider.ONEMINAI
    stream_options = {"include_usage": True}

    def _init_client(self):
        self.headers = {
            "API-KEY": self.config.api_key,
            "Content-Type": "application/json",
        }
        self.base_url = self.config.base_url

    async def _make_request(
        self,
        convo: Convo,
        temperature: Optional[float] = None,
        json_mode: bool = False,
    ) -> str:
        # Convert array of messages (dicts) to a single string
        combined_prompt = " ".join([msg.get("content", "") for msg in convo.messages])
        
        # Prepare the request body for 1min.ai
        request_body = {
            "type": "CHAT_WITH_AI",
            "conversationId": self.config.extra.get("conversation_id"),
            "model": self.config.model,
            "promptObject": {
                "prompt": combined_prompt,
                "isMixed": False,
                "webSearch": False
            }
        }
        # Send the request using the requests library
        response = requests.post(
            self.base_url,
            json=request_body,
            headers=self.headers,
            timeout=(self.config.connect_timeout, self.config.read_timeout),
        )

        # Check if the request was successful
        if response.status_code != 200:
            print(response.text)
            log.error(f"Request failed with status {response.status_code}: {response.text}")
            response.raise_for_status()

        # Extract response text from the JSON response
        response_str = response.text

        return response_str, 0, 0

    def rate_limit_sleep(self, err: requests.exceptions.RequestException) -> Optional[datetime.timedelta]:
        """
        Rate limit handling logic, adjusted to work with 1min.ai response format.
        """
        headers = err.response.headers
        if "x-ratelimit-remaining-tokens" not in headers:
            return None

        remaining_tokens = headers.get("x-ratelimit-remaining-tokens", 0)
        time_regex = r"(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?"
        
        if int(remaining_tokens) == 0:
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


__all__ = ["OneMinAIClient"]