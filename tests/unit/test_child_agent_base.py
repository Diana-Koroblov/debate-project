"""Unit tests for the ChildDebaterAgent and WebSearchMixin."""

from __future__ import annotations

from multiprocessing import Queue
from unittest.mock import MagicMock, patch

import pytest

from debate_sdk.services.child_agent import ChildDebaterAgent
from debate_sdk.services.web_search_mixin import WebSearchMixin
from debate_sdk.shared.contracts import ParentToChildRouter


class StubDebater(ChildDebaterAgent):
    """Concrete implementation for testing the abstraction."""
    def _execute_turn(self, prompt: ParentToChildRouter) -> None:
        self.turn_executed = True
        self.last_prompt = prompt


@pytest.fixture
def mock_config():
    """Mock configuration."""
    return {"version": "1.00", "watchdog": {"timeout_seconds": 10}, "debate": {}}


def test_web_search_mixin_aggregation():
    """Test that the mixin aggregates unique results."""
    mixin = WebSearchMixin()

    mock_results = [
        {"url": "site1.com", "title": "T1", "content": "C1"},
        {"url": "site2.com", "title": "T2", "content": "C2"}
    ]

    with patch.object(mixin._search_client, "search", return_value=mock_results):
        # Even with 2 identical queries, we should get unique URLs
        results = mixin.perform_research(["q1", "q1"])
        assert len(results) == 2
        assert results[0]["url"] == "site1.com"


def test_child_agent_handle_turn_prompt(mock_config):
    """Test that ChildDebaterAgent routes turn prompts correctly."""
    inbound, outbound = Queue(), Queue()
    agent = StubDebater("test_pro", mock_config, inbound, outbound)
    agent.turn_executed = False

    msg = ParentToChildRouter(
        recipient_id="test_pro",
        history=[],
        game_status="ACTIVE"
    )

    agent.handle_message(msg)
    assert agent.turn_executed is True
    assert agent.last_prompt == msg


def test_child_agent_emit_argument(mock_config):
    """Test serialization and emission of arguments."""
    inbound, outbound = Queue(), Queue()
    agent = StubDebater("test_con", mock_config, inbound, outbound)

    agent.emit_argument(text="Argument 1", round_num=1)

    msg = outbound.get(timeout=1.0)
    assert msg["type"] == "argument"
    assert msg["agent_id"] == "test_con"
    assert msg["payload"]["text"] == "Argument 1"


def test_web_search_mixin_format_citations():
    """Test converting raw results to Citation models."""
    mixin = WebSearchMixin()
    raw = [{"title": "NASA", "url": "nasa.gov"}]
    citations = mixin.format_citations(raw)
    assert len(citations) == 1
    assert citations[0].title == "NASA"


def test_child_agent_execute_turn_coverage(mock_config):
    """Test the template method _execute_turn."""
    inbound, outbound = Queue(), Queue()
    agent = ChildDebaterAgent("tester", mock_config, inbound, outbound)
    # Mock generate_argument which is usually provided by subclasses/mixins
    agent.generate_argument = MagicMock(
        return_value=(
            '{"text": "Sentence one. Sentence two. Sentence three. Sentence four."}'
        )
    )
    prompt = ParentToChildRouter(
        recipient_id="tester",
        history=["pro_agent: Earth may not be unique."],
        game_status="ACTIVE",
    )
    agent._execute_turn(prompt)
    assert agent.generate_argument.called
    called_prompt = agent.generate_argument.call_args[0][0]
    assert "Latest opponent statement" in called_prompt
    assert "2-3 concise sentences" in called_prompt

    msg = outbound.get(timeout=1.0)
    assert msg["payload"]["text"] == "Sentence one. Sentence two. Sentence three."


def test_child_agent_clamps_word_count(mock_config):
    """Test that long model outputs are shortened to a compact turn."""
    inbound, outbound = Queue(), Queue()
    agent = ChildDebaterAgent("tester", mock_config, inbound, outbound)
    long_text = " ".join([f"word{i}" for i in range(70)]) + "."
    agent.generate_argument = MagicMock(return_value=f'{{"text": "{long_text}"}}')

    prompt = ParentToChildRouter(
        recipient_id="tester",
        history=["con_agent: Current evidence is insufficient."],
        game_status="ACTIVE",
    )
    agent._execute_turn(prompt)

    msg = outbound.get(timeout=1.0)
    assert len(msg["payload"]["text"].split()) == 48


def test_child_agent_preserves_sentence_boundaries_when_possible(mock_config):
    """Test that sentence-boundary clamping prefers complete sentences."""
    inbound, outbound = Queue(), Queue()
    agent = ChildDebaterAgent("tester", mock_config, inbound, outbound)
    very_long_tail = " ".join([f"overflow{i}" for i in range(60)])
    agent.generate_argument = MagicMock(
        return_value=(
            '{"text": "Short first sentence. Short second sentence. This third sentence '
            + very_long_tail
            + '."}'
        )
    )

    prompt = ParentToChildRouter(
        recipient_id="tester",
        history=["con_agent: Current evidence is insufficient."],
        game_status="ACTIVE",
    )
    agent._execute_turn(prompt)

    msg = outbound.get(timeout=1.0)
    assert msg["payload"]["text"] == "Short first sentence. Short second sentence."


def test_child_agent_ignores_other_messages(mock_config):
    """Test that other message types are logged/ignored."""
    inbound, outbound = Queue(), Queue()
    agent = StubDebater("tester", mock_config, inbound, outbound)
    agent.turn_executed = False

    # This should be ignored by the debater (it's a parent message type)
    from debate_sdk.shared.contracts import ArgumentPayload, ChildToParentMessage
    msg = ChildToParentMessage(
        agent_id="other",
        round_number=1,
        payload=ArgumentPayload(text="should ignore")
    )

    agent.handle_message(msg)
    assert agent.turn_executed is False
