"""Mixin providing internet search capabilities to agents."""

from __future__ import annotations

from typing import Dict, List

from debate_sdk.shared.contracts import Citation
from debate_sdk.shared.search_client import SearchClient


class WebSearchMixin:
    """
    Encapsulates real-time search functionality for debater agents.

    This mixin allows agents to gather factual evidence and source
    citations to strengthen their arguments.
    """

    def __init__(self) -> None:
        """Initialize the search client."""
        self._search_client = SearchClient()

    def perform_research(self, queries: List[str]) -> List[Dict[str, str]]:
        """
        Execute multiple search queries and aggregate unique results.

        Args:
            queries (List[str]): List of research questions to investigate.

        Returns:
            List[Dict[str, str]]: Aggregated list of citations.
        """
        all_results = []
        seen_urls = set()

        for query in queries:
            results = self._search_client.search(query, max_results=3)
            for res in results:
                url = res.get("url", "#")
                if url not in seen_urls:
                    seen_urls.add(url)
                    all_results.append(res)

        return all_results

    def format_citations(self, raw_results: List[Dict[str, str]]) -> List[Citation]:
        """
        Convert raw search results into validated Citation models.

        Args:
            raw_results (List[Dict[str, str]]): List of title/url/content dicts.

        Returns:
            List[Citation]: List of Pydantic Citation models.
        """
        return [
            Citation(
                title=res.get("title", "Untitled"),
                url=res.get("url", "#")
            ) for res in raw_results
        ]
