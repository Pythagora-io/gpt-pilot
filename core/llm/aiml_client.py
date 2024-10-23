from httpx import Timeout
from openai import AsyncOpenAI

from core.config import LLMProvider
from core.llm.openai_client import OpenAIClient
from core.log import get_logger

log = get_logger(__name__)


class AIMLClient(OpenAIClient):
    provider = LLMProvider.AIML
    stream_options = None

    def _init_client(self):
        self.client = AsyncOpenAI(
            api_key=self.config.api_key,
            base_url=self.config.base_url,
            timeout=Timeout(
                max(self.config.connect_timeout, self.config.read_timeout),
                connect=self.config.connect_timeout,
                read=self.config.read_timeout,
            ),
        )
