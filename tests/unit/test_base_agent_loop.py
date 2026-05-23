"""Unit tests for the BaseAgent autonomous event loop."""

from __future__ import annotations

import queue
from multiprocessing import Queue
from typing import Any, Dict
from unittest.mock import patch

import pytest

from debate_sdk.services.base_agent import BaseAgent
from debate_sdk.shared.contracts import AnyMessage, MessageType


class ConcreteAgent(BaseAgent):
    """Concrete implementation for testing purposes."""

    def __init__(
        self,
        agent_id: str,
        config: Dict[str, Any],
        inbound: Queue,
        outbound: Queue
    ) -> None:
        super().__init__(agent_id, config, inbound, outbound)
        self.last_message = None

    def handle_message(self, message: AnyMessage) -> None:
        """Capture the message for assertion."""
        if message.type == MessageType.ARGUMENT and message.agent_id == "trigger_super":
            super().handle_message(message)
        self.last_message = message


@pytest.fixture
def mock_config() -> Dict[str, Any]:
    """Provide a mock configuration dictionary."""
    return {"version": "1.00", "watchdog": {"timeout_seconds": 10}, "debate": {}}


def test_base_agent_run_loop_valid(mock_config):
    """Test the event loop with a valid message."""
    inbound, outbound = Queue(), Queue()
    agent = ConcreteAgent("loop_agent", mock_config, inbound, outbound)

    msg = {
        "type": "turn_prompt",
        "recipient_id": "loop_agent",
        "history": [],
        "game_status": "ACTIVE"
    }
    inbound.put(msg)

    # Use a real method but terminate after it's called
    original_handle = agent.handle_message

    def mock_handle(m):
        original_handle(m)
        agent.terminate()

    with patch.object(agent, "handle_message", side_effect=mock_handle):
        agent.run()

    assert agent.last_message.recipient_id == "loop_agent"


def test_base_agent_run_loop_exception(mock_config):
    """Test that a critical exception in the loop triggers termination."""
    inbound, outbound = Queue(), Queue()
    agent = ConcreteAgent("err_agent", mock_config, inbound, outbound)
    with patch.object(inbound, "get", side_effect=RuntimeError("BOOM")):
        agent.run()
    assert agent.is_running is False


def test_base_agent_abstract_call(mock_config):
    """Test that calling the base handle_message raises NotImplementedError."""
    agent = ConcreteAgent("abstract_tester", mock_config, Queue(), Queue())
    with pytest.raises(NotImplementedError):
        from debate_sdk.shared.contracts import ArgumentPayload, ChildToParentMessage
        msg = ChildToParentMessage(
            agent_id="trigger_super",
            round_number=1,
            payload=ArgumentPayload(text="test")
        )
        agent.handle_message(msg)


def test_base_agent_run_loop_timeout_continue(mock_config):
    """Test the event loop handling a queue timeout and continuing."""
    inbound = Queue()
    agent = ConcreteAgent("timeout_agent", mock_config, inbound, Queue())
    with patch.object(inbound, "get") as mock_get:
        def side_effect(timeout):
            if mock_get.call_count == 1:
                raise queue.Empty
            agent.terminate()
            raise queue.Empty
        mock_get.side_effect = side_effect
        agent.run()
    assert mock_get.call_count == 2
