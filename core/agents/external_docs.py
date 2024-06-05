import asyncio
from urllib.parse import urljoin

import httpx

from core.agents.base import BaseAgent
from core.agents.convo import AgentConvo
from core.agents.response import AgentResponse
from core.config import EXTERNAL_DOCUMENTATION_API
from core.log import get_logger
from core.telemetry import telemetry

log = get_logger(__name__)


class ExternalDocumentation(BaseAgent):
    """Agent in charge of collecting and storing additional documentation.

    Docs are per task and are stores in the `tasks` variable in the project state.
    This agent ensures documentation is collected only once per task.

    Agent does 2 LLM interactions:
        1. Ask the LLM to select useful documentation from a predefined list.
        2. Ask the LLM to come up with a query to use to fetch the actual documentation snippets.

    """

    agent_type = "external-docs"
    display_name = "Documentation"

    async def run(self) -> AgentResponse:
        current_task = self.current_state.current_task
        if not current_task:
            # If we have no active task, there's no docs to collect
            return AgentResponse.done(self)

        available_docsets = await self._get_available_docsets()
        selected_docsets = await self._select_docsets(available_docsets)
        if not selected_docsets:
            await self._store_docs([], available_docsets)
            return AgentResponse.done(self)
        telemetry.set("docsets_used", selected_docsets)

        queries = await self._create_queries(selected_docsets)
        doc_snippets = await self._fetch_snippets(queries)
        telemetry.set("doc_snippets_stored", len(doc_snippets))

        await self._store_docs(doc_snippets, available_docsets)
        return AgentResponse.done(self)

    async def _get_available_docsets(self) -> list[tuple]:
        url = urljoin(EXTERNAL_DOCUMENTATION_API, "docsets")
        resp = httpx.get(url)
        log.debug(f"Fetched {len(resp.json())} docsets.")
        return resp.json()

    async def _select_docsets(self, available_docsets: list[tuple]) -> dict[str, str]:
        llm = self.get_llm()
        convo = AgentConvo(self).template(
            "select_docset",
            current_task=self.current_state.current_task,
            available_docsets=available_docsets,
        )
        llm_response: str = await llm(convo)
        available_docsets = dict(available_docsets)
        if llm_response.strip().lower() == "done":
            return {}
        else:
            selected_keys = llm_response.splitlines()
            return {k: available_docsets[k] for k in selected_keys}

    async def _create_queries(self, docsets: dict[str, str]) -> dict[str, list[str]]:
        """Return queries we have to make to the docs API.

        Key is the docset_key and value is the list of queries for that docset.

        """
        queries = {}
        for k, short_desc in docsets.items():
            llm = self.get_llm()
            convo = AgentConvo(self).template(
                "create_queries",
                short_description=short_desc,
                current_task=self.current_state.current_task,
            )
            llm_response: str = await llm(convo)
            if llm_response.strip().lower() == "done":
                continue
            else:
                queries[k] = llm_response.splitlines()

        return queries

    async def _fetch_snippets(self, queries: dict[str, list[str]]) -> list[tuple]:
        """Query the docs API and fetch the documentation snippets.

        Returns a list of tuples: (docset_key, snippets).

        """
        url = urljoin(EXTERNAL_DOCUMENTATION_API, "query")

        snippets: list[tuple] = []
        async with httpx.AsyncClient() as client:
            reqs = []
            ordered_keys = []
            for docset_key, qs in queries.items():
                reqs.append(client.get(url, params={"q": qs, "doc_key": docset_key}))
                ordered_keys.append(docset_key)

            results = await asyncio.gather(*reqs)

        for k, res in zip(ordered_keys, results):
            snippets.append((k, res.json()))
        return snippets

    async def _store_docs(self, snippets: list[tuple], available_docsets: list[tuple]):
        """Store the snippets into current task data.

        Documentation snippets are stored as a list of dictionaries:
        {"key": docset-key, "desc": documentation-description, "snippets": list-of-snippets}

        """

        docsets_dict = dict(available_docsets)
        docs = []
        for docset_key, snip in snippets:
            docs.append({"key": docset_key, "desc": docsets_dict[docset_key], "snippets": snip})

        self.next_state.current_task["docs"] = docs
        self.next_state.flag_tasks_as_modified()
