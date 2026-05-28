"""Unit tests for Child Agents (Pro & Con) and their tool capabilities."""

from __future__ import annotations

from multiprocessing import Queue
from unittest.mock import MagicMock, patch

import pytest

from debate_sdk.services.con_agent import ConDebaterAgent
from debate_sdk.services.pro_agent import ProDebaterAgent
from debate_sdk.shared.contracts import MessageType, ParentToChildRouter


@pytest.fixture
def mock_config():
    """Shared mock configuration for agents."""
    return {
        "version": "1.00",
        "debate": {
            "model": "llama-3.1-8b-instant",
            "pro_persona": "Pro Persona",
            "con_persona": "Con Persona",
            "adversarial_rules": ["Rule 1"],
            "formatting_instructions": "JSON please"
        }
    }


def _mock_groq_response(mock_client_cls, content: str) -> None:
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {
        "choices": [{"message": {"content": content}}],
        "usage": {"prompt_tokens": 11, "completion_tokens": 7},
    }
    mock_client_cls.return_value.post.return_value = mock_response

def test_child_agent_search_mock(mock_config):
    """
    5.6.2: Write a test case utilizing a MockEngine to simulate a Search API response,
    asserting that the agent correctly parses the mock data payload.
    """
    with patch("debate_sdk.services.groq_mixin.httpx.Client"):
        agent = ProDebaterAgent("pro_1", mock_config, Queue(), Queue())

        mock_results = [
            {"title": "Found Life", "url": "https://aliens.com", "content": "Evidence found."}
        ]

        with patch.object(agent._search_client, "search", return_value=mock_results):
            research = agent.perform_research(["Is there life?"])
            assert len(research) == 1
            assert research[0]["title"] == "Found Life"

            citations = agent.format_citations(research)
            assert len(citations) == 1
            assert citations[0].title == "Found Life"
            assert citations[0].url == "https://aliens.com"

def test_pro_agent_contract_compliance(mock_config):
    """
    5.6.3: Construct a validation test passing an opponent's message block to ProDebaterAgent,
    asserting that its generated output complies with the ChildToParentMessage structural contract.
    """
    outbound = Queue()
    with patch("debate_sdk.services.groq_mixin.httpx.Client") as mock_client_cls:
        _mock_groq_response(
            mock_client_cls,
            '{"text": "Rebuttal: No evidence for silence.", "citations": []}',
        )

        agent = ProDebaterAgent("pro_v1", mock_config, Queue(), outbound)

        prompt = ParentToChildRouter(
            recipient_id="pro_v1",
            history=["Opponent: Space is empty."],
            game_status="ACTIVE"
        )

        agent._execute_turn(prompt)

        msg = outbound.get(timeout=1.0)
        # Verify the structure matches ChildToParentMessage (implicitly via emit_argument logic)
        assert msg["type"] == MessageType.ARGUMENT
        assert msg["agent_id"] == "pro_v1"
        assert "payload" in msg
        assert msg["payload"]["text"] == "Rebuttal: No evidence for silence."

def test_con_agent_contract_compliance(mock_config):
    """
    5.6.4: Construct an identical validation test for ConDebaterAgent,
    verifying character consistency and compliance.
    """
    outbound = Queue()
    with patch("debate_sdk.services.groq_mixin.httpx.Client") as mock_client_cls:
        _mock_groq_response(
            mock_client_cls,
            '{"text": "Rebuttal: Drake equation is speculation.", "citations": []}',
        )

        agent = ConDebaterAgent("con_v1", mock_config, Queue(), outbound)

        prompt = ParentToChildRouter(
            recipient_id="con_v1",
            history=["Opponent: Drake says billions."],
            game_status="ACTIVE"
        )

        agent._execute_turn(prompt)

        msg = outbound.get(timeout=1.0)
        assert msg["type"] == MessageType.ARGUMENT
        assert msg["payload"]["text"] == "Rebuttal: Drake equation is speculation."

def test_schema_violation_graceful_handling(mock_config):
    """
    5.6.5: Assert that any runtime text emissions violating the schema format are
    dropped by the internal sdk exception-handlers without bringing down the running process thread.
    """
    import queue
    outbound = Queue()
    with patch("debate_sdk.services.groq_mixin.httpx.Client") as mock_client_cls:
        _mock_groq_response(mock_client_cls, "NOT JSON AT ALL")

        agent = ProDebaterAgent("pro_fail", mock_config, Queue(), outbound)

        prompt = ParentToChildRouter(recipient_id="pro_fail", game_status="ACTIVE")

        # Should NOT raise exception, but log error and DROP the packet
        agent._execute_turn(prompt)

        # Verify NOTHING was sent to the outbound queue
        with pytest.raises(queue.Empty):
            outbound.get(timeout=0.1)

        # The process didn't crash and is ready for next turn
