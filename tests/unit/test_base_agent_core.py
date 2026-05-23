"""Unit tests for the BaseAgent core initialization and lifecycle."""

from __future__ import annotations

from multiprocessing import Queue
from typing import Any, Dict

import pytest

from debate_sdk.services.base_agent import BaseAgent
from debate_sdk.shared.contracts import AnyMessage


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
        self.last_message = message


@pytest.fixture
def mock_config() -> Dict[str, Any]:
    """Provide a mock configuration dictionary."""
    return {
        "version": "1.00",
        "watchdog": {"timeout_seconds": 10, "check_interval_seconds": 2},
        "debate": {"rounds": 10}
    }


def test_base_agent_initialization(mock_config):
    """Test that the base agent initializes correctly with queues."""
    inbound, outbound = Queue(), Queue()
    agent = ConcreteAgent("test_agent", mock_config, inbound, outbound)

    assert agent.agent_id == "test_agent"
    assert agent.config == mock_config
    assert agent.inbound_queue == inbound
    assert agent.outbound_queue == outbound
    assert agent.is_running is False


def test_base_agent_terminate(mock_config):
    """Test the terminate signal."""
    inbound, outbound = Queue(), Queue()
    agent = ConcreteAgent("killer", mock_config, inbound, outbound)
    agent.is_running = True
    agent.terminate()
    assert agent.is_running is False
