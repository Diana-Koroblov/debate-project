"""Web search client utility for real-time internet intelligence."""

from __future__ import annotations

import os
import re
from typing import Any, Dict, List

import httpx
from dotenv import load_dotenv

from debate_sdk.shared.logger import setup_logger

load_dotenv()
logger = setup_logger("search_client")


class SearchClient:
    """
    Interface for external search providers (Tavily).

    This client handles the secure communication with the Search API,
    enforcing timeouts and structured result parsing.

    Attributes:
        api_key (str): Secure credential loaded from environment.
        endpoint (str): API URL for search requests.
        timeout (float): Max seconds to wait for a response.
    """

    def __init__(self, timeout: float = 15.0) -> None:
        """
        Initialize the search client.

        Args:
            timeout (float): Response timeout in seconds.
        """
        self.api_key = os.getenv("TAVILY_API_KEY", "")
        self.endpoint = "https://api.tavily.com/search"
        self.timeout = timeout

        if not self.api_key:
            logger.warning("TAVILY_API_KEY not found in environment.")

    def _sanitize_query(self, query: str) -> str:
        """
        Clean the search query to prevent injection or malformed requests.

        Args:
            query (str): The raw user/agent query.

        Returns:
            str: The sanitized query string.
        """
        # Remove non-printable characters and excess whitespace
        sanitized = re.sub(r"[^\x20-\x7E]", "", query)
        return sanitized.strip()

    def search(self, query: str, max_results: int = 5) -> List[Dict[str, str]]:
        """
        Execute a real-time web search.

        Args:
            query (str): The research query.
            max_results (int): Max number of citations to retrieve.

        Returns:
            List[Dict[str, str]]: Parsed results containing 'title', 'url', 'content'.
        """
        if not self.api_key:
            logger.error("Search failed: Missing API Key.")
            return []

        clean_query = self._sanitize_query(query)
        if not clean_query:
            return []

        payload = {
            "api_key": self.api_key,
            "query": clean_query,
            "max_results": max_results,
            "search_depth": "basic"
        }

        logger.info(f"Executing search for: '{clean_query}'")
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(self.endpoint, json=payload)
                response.raise_for_status()
                data = response.json()
                return self._parse_results(data.get("results", []))
        except httpx.TimeoutException:
            logger.error(f"Search timed out after {self.timeout}s")
        except Exception as exc:
            logger.error(f"Search execution error: {exc}")

        return []

    def _parse_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """
        Format raw API results into the system's standard citation schema.

        Args:
            results (List[Dict[str, Any]]): Raw list from API.

        Returns:
            List[Dict[str, str]]: Cleaned and verified results.
        """
        parsed = []
        for res in results:
            parsed.append({
                "title": str(res.get("title", "Untitled")),
                "url": str(res.get("url", "#")),
                "content": str(res.get("content", ""))
            })
        return parsed
