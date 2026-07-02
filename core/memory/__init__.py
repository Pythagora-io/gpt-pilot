"""
Optional project memory backed by a Dakera memory server (https://dakera.ai).

Pythagora builds applications iteratively across many separate conversations. Each
new conversation re-loads project context from the spec and the file tree, but the
*reasoning* from earlier sessions -- architectural decisions, debugging resolutions,
conventions that were agreed on -- is not carried over and gets re-derived from
scratch. `ProjectMemory` gives Pythagora a lightweight, self-hosted semantic memory:

* on task breakdown it recalls the decisions/bug-fixes most relevant to the task and
  offers them to the Developer agent as extra context, and
* on task completion it stores a short summary of the outcome.

The integration is fully opt-in (see :class:`core.config.DakeraConfig`) and every
network call is best-effort: a slow or unreachable server logs a warning and degrades
to "no memory", exactly like :class:`core.agents.external_docs.ExternalDocumentation`
degrades when the docs API is down. It never blocks or fails a build.
"""

from typing import Optional

import httpx

from core.config import DakeraConfig, get_config
from core.log import get_logger

log = get_logger(__name__)


class RecalledMemory:
    """A single memory returned by the Dakera server, trimmed to what the prompt needs."""

    def __init__(self, content: str, importance: float, score: float):
        self.content = content
        self.importance = importance
        self.score = score


class ProjectMemory:
    """
    Thin async client for the two Dakera REST endpoints Pythagora uses:

    * ``POST /v1/memory/recall`` -- semantic recall of prior memories for a query.
    * ``POST /v1/memory/store``  -- persist a memory.

    Memories are namespaced per project via ``agent_id = "gptpilot-<project_id>"`` so
    that recall only ever surfaces knowledge from the same project.
    """

    def __init__(self, config: DakeraConfig, project_id: str):
        self.config = config
        self.agent_id = f"gptpilot-{project_id}"
        self._timeout = httpx.Timeout(
            connect=config.connect_timeout,
            read=config.read_timeout,
            write=config.read_timeout,
            pool=config.connect_timeout,
        )

    @classmethod
    def for_project(cls, project_id: Optional[str]) -> Optional["ProjectMemory"]:
        """
        Build a :class:`ProjectMemory` from the global config, or ``None`` if memory
        is not configured/enabled. Callers use the ``None`` result to skip the feature
        entirely, so default (memory-less) behaviour is completely unchanged.
        """
        config = get_config().memory
        if config is None or not config.enabled or not project_id:
            return None
        return cls(config, str(project_id))

    def _headers(self) -> dict:
        headers = {"Content-Type": "application/json"}
        if self.config.api_key:
            headers["X-API-Key"] = self.config.api_key
        return headers

    def _url(self, path: str) -> str:
        return f"{self.config.base_url.rstrip('/')}{path}"

    async def recall(self, query: str, top_k: Optional[int] = None) -> list[RecalledMemory]:
        """
        Recall up to ``top_k`` memories most relevant to ``query`` for this project.

        Returns an empty list if memory is unavailable for any reason (this method
        never raises), so callers can use the result unconditionally.
        """
        if not query:
            return []

        payload = {
            "agent_id": self.agent_id,
            "query": query,
            "top_k": top_k or self.config.top_k,
        }
        try:
            async with httpx.AsyncClient(
                transport=httpx.AsyncHTTPTransport(retries=3),
                timeout=self._timeout,
            ) as client:
                response = await client.post(
                    self._url("/v1/memory/recall"),
                    json=payload,
                    headers=self._headers(),
                )
                response.raise_for_status()
                data = response.json()
        except (httpx.HTTPError, ValueError):
            log.warning("Dakera recall failed; continuing without project memory", exc_info=True)
            return []

        memories = []
        for result in data.get("memories", []):
            memory = result.get("memory", {})
            content = memory.get("content")
            if not content:
                continue
            memories.append(
                RecalledMemory(
                    content=content,
                    importance=memory.get("importance", 0.0),
                    # Prefer the importance-weighted score when the server provides it.
                    score=result.get("weighted_score") or result.get("score", 0.0),
                )
            )
        log.debug(f"Recalled {len(memories)} memories for agent {self.agent_id}")
        return memories

    async def store(self, content: str, tags: Optional[list[str]] = None) -> bool:
        """
        Store a memory for this project. Returns ``True`` on success, ``False`` if the
        server was unavailable. Never raises.
        """
        if not content:
            return False

        payload = {
            "agent_id": self.agent_id,
            "content": content,
            "importance": self.config.min_importance,
            "tags": tags or ["gpt-pilot"],
        }
        try:
            async with httpx.AsyncClient(
                transport=httpx.AsyncHTTPTransport(retries=3),
                timeout=self._timeout,
            ) as client:
                response = await client.post(
                    self._url("/v1/memory/store"),
                    json=payload,
                    headers=self._headers(),
                )
                response.raise_for_status()
        except httpx.HTTPError:
            log.warning("Dakera store failed; task outcome not persisted to project memory", exc_info=True)
            return False

        log.debug(f"Stored memory for agent {self.agent_id}")
        return True
