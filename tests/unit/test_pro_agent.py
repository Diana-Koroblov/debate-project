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
            "model": "gemini-test",
            "pro_persona": "Test Persona"
        }
    }


def test_pro_agent_initialization(mock_config):
    """Test that the pro agent initializes correctly."""
    with patch("google.generativeai.GenerativeModel"):
        agent = ProDebaterAgent("pro_1", mock_config, Queue(), Queue())
        assert agent.agent_id == "pro_1"
        assert agent._model is not None


def test_pro_agent_execute_turn(mock_config):
    """Test the turn execution and argument emission."""
    inbound, outbound = Queue(), Queue()

    with patch("google.generativeai.GenerativeModel") as mock_model_cls:
        # Setup mock chat response
        mock_model = mock_model_cls.return_value
        mock_chat = mock_model.start_chat.return_value
        mock_response = MagicMock()
        mock_response.text = '{"text": "Life is everywhere.", "citations": []}'
        mock_chat.send_message.return_value = mock_response

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
