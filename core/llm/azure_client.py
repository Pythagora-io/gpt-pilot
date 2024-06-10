from httpx import Timeout
from openai import AsyncAzureOpenAI

from core.config import LLMProvider
from core.llm.openai_client import OpenAIClient
from core.log import get_logger

log = get_logger(__name__)


class AzureClient(OpenAIClient):
    provider = LLMProvider.AZURE
    stream_options = None

    def _init_client(self):
        azure_deployment = self.config.extra.get("azure_deployment")
        api_version = self.config.extra.get("api_version")

        self.client = AsyncAzureOpenAI(
            api_key=self.config.api_key,
            azure_endpoint=self.config.base_url,
            azure_deployment=azure_deployment,
            api_version=api_version,
            timeout=Timeout(
                max(self.config.connect_timeout, self.config.read_timeout),
                connect=self.config.connect_timeout,
                read=self.config.read_timeout,
            ),
        )
