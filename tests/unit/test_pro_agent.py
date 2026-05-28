"""Unit tests for the ProDebaterAgent."""

from __future__ import annotations

from multiprocessing import Queue
from unittest.mock import MagicMock, patch

import pytest

from debate_sdk.services.pro_agent import ProDebaterAgent
from debate_sdk.shared.contracts import ParentToChildRouter


@pytest.fixture
def mock_config():
    """Mock configuration."""
    return {
        "version": "1.00",
        "watchdog": {"timeout_seconds": 10},
        "debate": {
            "model": "llama-3.1-8b-instant",
            "pro_persona": "Test Persona"
        }
    }


def _mock_groq_response(mock_client_cls, content: str) -> None:
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {
        "choices": [{"message": {"content": content}}],
        "usage": {"prompt_tokens": 8, "completion_tokens": 4},
    }
    mock_client_cls.return_value.post.return_value = mock_response


def test_pro_agent_initialization(mock_config):
    """Test that the pro agent initializes correctly."""
    with patch("debate_sdk.services.groq_mixin.httpx.Client"):
        agent = ProDebaterAgent("pro_1", mock_config, Queue(), Queue())
        assert agent.agent_id == "pro_1"
        assert agent._model is not None


def test_pro_agent_execute_turn(mock_config):
    """Test the turn execution and argument emission."""
    inbound, outbound = Queue(), Queue()

    with patch("debate_sdk.services.groq_mixin.httpx.Client") as mock_client_cls:
        _mock_groq_response(mock_client_cls, '{"text": "Life is everywhere.", "citations": []}')

        agent = ProDebaterAgent("pro_v1", mock_config, inbound, outbound)

        prompt = ParentToChildRouter(
            recipient_id="pro_v1",
            history=["Opponent: Why life?", "Me: Because stats."],
            game_status="ACTIVE"
        )

        agent._execute_turn(prompt)

        # Verify argument reached outbound queue
        msg = outbound.get(timeout=1.0)
        assert msg["type"] == "argument"
        assert msg["payload"]["text"] == "Life is everywhere."
        assert msg["round_number"] == 2
