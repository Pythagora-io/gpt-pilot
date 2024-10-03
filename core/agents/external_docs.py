import asyncio
from urllib.parse import urljoin

import httpx
from pydantic import BaseModel

from core.agents.base import BaseAgent
from core.agents.convo import AgentConvo
from core.agents.response import AgentResponse
from core.config import EXTERNAL_DOCUMENTATION_API
from core.llm.parser import JSONParser
from core.log import get_logger
from core.telemetry import telemetry

log = get_logger(__name__)


class DocQueries(BaseModel):
    queries: list[str]


class SelectedDocsets(BaseModel):
    docsets: list[str]


class ExternalDocumentation(BaseAgent):
    """Agent in charge of collecting and storing additional documentation.

    Docs are per task and are stores in the `docs` variable in the project state.
    This agent ensures documentation is collected only once per task.

    Agent does 2 LLM interactions:
        1. Ask the LLM to select useful documentation from a predefined list.
        2. Ask the LLM to come up with a query to use to fetch the actual documentation snippets.

    Agent does 2 calls to our documentation API:
        1. Fetch all the available docsets. `docset` is a collection of documentation snippets
           for a single topic, eg. VueJS API Reference docs.
        2. Fetch the documentation snippets for given queries.

    """

    agent_type = "external-docs"
    display_name = "Documentation"

    async def run(self) -> AgentResponse:
        await self._store_docs([], [])
        return AgentResponse.done(self)

        if self.current_state.specification.example_project:
            log.debug("Example project detected, no documentation selected.")
            available_docsets = []
        else:
            available_docsets = await self._get_available_docsets()

        selected_docsets = await self._select_docsets(available_docsets)
        await telemetry.trace_code_event("docsets_used", selected_docsets)

        if not selected_docsets:
            log.info("No documentation selected for this task.")
            await self._store_docs([], available_docsets)
            return AgentResponse.done(self)

        log.info(f"Selected {len(selected_docsets)} docsets for this task.")
        queries = await self._create_queries(selected_docsets)
        doc_snippets = await self._fetch_snippets(queries)
        await telemetry.trace_code_event("doc_snippets", {"num_stored": len(doc_snippets)})

        await self._store_docs(doc_snippets, available_docsets)
        return AgentResponse.done(self)

    async def _get_available_docsets(self) -> list[tuple]:
        url = urljoin(EXTERNAL_DOCUMENTATION_API, "docsets")
        client = httpx.Client(transport=httpx.HTTPTransport(retries=3))
        try:
            resp = client.get(url)
        except httpx.HTTPError:
            # In case of any errors, we'll proceed without the documentation
            log.warning("Failed to fetch available docsets due to an error.", exc_info=True)
            return []

        log.debug(f"Fetched {len(resp.json())} docsets.")
        return resp.json()

    async def _select_docsets(self, available_docsets: list[tuple]) -> dict[str, str]:
        """From a list of available docsets, select the relevant ones."""

        if not available_docsets:
            return {}

        llm = self.get_llm(stream_output=True)
        convo = (
            AgentConvo(self)
            .template(
                "select_docset",
                current_task=self.current_state.current_task,
                available_docsets=available_docsets,
            )
            .require_schema(SelectedDocsets)
        )
        await self.send_message("Determining if external documentation is needed for the next task...")
        llm_response: SelectedDocsets = await llm(convo, parser=JSONParser(spec=SelectedDocsets))
        available_docsets = dict(available_docsets)
        return {k: available_docsets[k] for k in llm_response.docsets if k in available_docsets}

    async def _create_queries(self, docsets: dict[str, str]) -> dict[str, list[str]]:
        """Return queries we have to make to the docs API.

        Key is the docset_key and value is the list of queries for that docset.

        """
        queries = {}
        await self.send_message("Getting relevant documentation for the following topics:")
        for k, short_desc in docsets.items():
            llm = self.get_llm(stream_output=True)
            convo = (
                AgentConvo(self)
                .template(
                    "create_docs_queries",
                    short_description=short_desc,
                    current_task=self.current_state.current_task,
                )
                .require_schema(DocQueries)
            )
            llm_response: DocQueries = await llm(convo, parser=JSONParser(spec=DocQueries))
            if llm_response.queries:
                queries[k] = llm_response.queries

        return queries

    async def _fetch_snippets(self, queries: dict[str, list[str]]) -> list[tuple]:
        """Query the docs API and fetch the documentation snippets.

        Returns a list of tuples: (docset_key, snippets).

        """
        url = urljoin(EXTERNAL_DOCUMENTATION_API, "query")
        snippets: list[tuple] = []
        async with httpx.AsyncClient(transport=httpx.AsyncHTTPTransport(retries=3)) as client:
            reqs = []
            ordered_keys = []
            for docset_key, qs in queries.items():
                reqs.append(client.get(url, params={"q": qs, "doc_key": docset_key, "num_results": 3}))
                ordered_keys.append(docset_key)

            try:
                results = await asyncio.gather(*reqs)
            except httpx.HTTPError:
                log.warning("Failed to fetch documentation snippets", exc_info=True)

        for k, res in zip(ordered_keys, results):
            json_snippets = res.json()
            log.debug(f"Fetched {len(json_snippets)} snippets from {k}")
            if len(json_snippets):
                snippets.append((k, res.json()))
        return snippets

    async def _store_docs(self, snippets: list[tuple], available_docsets: list[tuple]):
        """Store the snippets into current task data.

        Documentation snippets are stored as a list of dictionaries:
        {"key": docset-key, "desc": documentation-description, "snippets": list-of-snippets}

        :param snippets: List of tuples: (docset_key, snippets)
        :param available_docsets: List of available docsets from the API.
        """

        docsets_dict = dict(available_docsets)
        docs = []
        for docset_key, snip in snippets:
            docs.append({"key": docset_key, "desc": docsets_dict[docset_key], "snippets": snip})

        self.next_state.docs = docs
