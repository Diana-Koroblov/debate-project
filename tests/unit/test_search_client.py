"""Unit tests for the SearchClient utility."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest

from debate_sdk.shared.search_client import SearchClient


@pytest.fixture
def mock_client():
    """Setup a search client with a dummy key."""
    with patch.dict("os.environ", {"TAVILY_API_KEY": "fake-key"}):
        return SearchClient(timeout=1.0)


def test_search_client_sanitization(mock_client):
    """Test query sanitization logic."""
    assert mock_client._sanitize_query("  Space exploration  \n") == "Space exploration"
    assert mock_client._sanitize_query("Alien\x00Life") == "AlienLife"


def test_search_client_parse_results(mock_client):
    """Test parsing raw API results into structured schema."""
    raw = [
        {"title": "T1", "url": "U1", "content": "C1"},
        {"title": "T2", "url": "U2"}  # Missing content
    ]
    parsed = mock_client._parse_results(raw)

    assert len(parsed) == 2
    assert parsed[0]["title"] == "T1"
    assert parsed[1]["content"] == ""


def test_search_client_success(mock_client):
    """Test successful search execution with mocking."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "results": [{"title": "Success", "url": "ok.com", "content": "found"}]
    }
    mock_response.raise_for_status.return_value = None

    with patch("httpx.Client.post", return_value=mock_response):
        results = mock_client.search("aliens")
        assert len(results) == 1
        assert results[0]["title"] == "Success"


def test_search_client_timeout(mock_client):
    """Test search client timeout handling."""
    with patch("httpx.Client.post", side_effect=httpx.TimeoutException("Too slow")):
        results = mock_client.search("slow query")
        assert results == []


def test_search_client_empty_query(mock_client):
    """Test search with an empty or whitespace-only query."""
    assert mock_client.search("") == []
    assert mock_client.search("   ") == []


def test_search_client_execution_error(mock_client):
    """Test handling of unexpected errors during search."""
    with patch("httpx.Client.post", side_effect=ValueError("Unexpected")):
        assert mock_client.search("fail query") == []


def test_search_client_missing_key():
    """Test behavior when API key is missing."""
    with patch.dict("os.environ", {"TAVILY_API_KEY": ""}, clear=True):
        client = SearchClient()
        assert client.search("test") == []
