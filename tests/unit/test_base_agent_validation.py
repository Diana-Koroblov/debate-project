"""Unit tests for BaseAgent IPC payload validation and telemetry."""

from __future__ import annotations

from multiprocessing import Queue
from typing import Any, Dict
from unittest.mock import MagicMock

import pytest

from debate_sdk.services.base_agent import BaseAgent
from debate_sdk.shared.contracts import MessageType


class ConcreteAgent(BaseAgent):
    """Concrete implementation for testing purposes."""
    def handle_message(self, message: Any) -> None:
        pass


@pytest.fixture
def mock_config() -> Dict[str, Any]:
    """Provide a mock configuration dictionary."""
    return {"version": "1.00", "watchdog": {"timeout_seconds": 10}, "debate": {}}


def test_validate_payload_valid_dict(mock_config):
    """Test validation with a valid dictionary."""
    agent = ConcreteAgent("val", mock_config, Queue(), Queue())
    valid_msg = {
        "type": "turn_prompt",
        "recipient_id": "val",
        "history": ["a"],
        "game_status": "ACTIVE"
    }
    model = agent._validate_payload(valid_msg)
    assert model is not None
    assert model.type == MessageType.TURN_PROMPT


def test_validate_payload_invalid(mock_config):
    """Test validation with invalid data (should return None)."""
    agent = ConcreteAgent("val", mock_config, Queue(), Queue())
    assert agent._validate_payload({"type": "unknown"}) is None
    assert agent._validate_payload("not-even-json") is None


def test_log_token_usage(mock_config):
    """Test emitting token telemetry."""
    outbound = Queue()
    agent = ConcreteAgent("tele_agent", mock_config, Queue(), outbound)
    agent.log_token_usage(input_tokens=10, output_tokens=20, latency_ms=100.0, model="m1")
    msg = outbound.get(timeout=1.0)
    assert msg["type"] == "telemetry"
    assert msg["usage"]["input"] == 10


def test_boundary_child_to_parent_message(mock_config):
    """Verify ChildToParentMessage validation (Task 4.6.3)."""
    agent = ConcreteAgent("boundary", mock_config, Queue(), Queue())
    valid_msg = {
        "type": "argument",
        "agent_id": "pro_1",
        "round_number": 1,
        "payload": {
            "text": "Space is big.",
            "search_queries": ["how big is space"],
            "citations": [{"title": "NASA", "url": "http://nasa.gov"}]
        }
    }
    model = agent._validate_payload(valid_msg)
    assert model is not None
    assert model.type == MessageType.ARGUMENT
    assert model.payload.text == "Space is big."


def test_send_message_failure(mock_config):
    """Test send_message failure handling."""
    outbound = MagicMock()
    outbound.put_nowait.side_effect = Exception("Queue full")
    agent = ConcreteAgent("fail", mock_config, Queue(), outbound)
    agent.send_message({"any": "thing"})
    assert outbound.put_nowait.called
