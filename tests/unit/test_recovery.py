"""Unit tests for the recovery mechanism triggered by Watchdog."""

from __future__ import annotations

import time
from typing import Any, Dict
from unittest.mock import MagicMock

import pytest

from debate_sdk.shared.recovery import RecoveryManager
from debate_sdk.shared.watchdog import Watchdog


def test_recovery_manager_flow():
    """Test the full recovery manager registration and recovery flow."""
    rm = RecoveryManager()

    def mock_factory(agent_id, state):
        return {"id": agent_id, "state": state, "status": "recovered"}

    rm.register_factory("pro", mock_factory)

    state = {"history": ["a"]}
    agent = rm.recover("pro_1", "pro", state)

    assert agent["id"] == "pro_1"
    assert agent["state"] == state
    assert agent["status"] == "recovered"


def test_recovery_manager_missing_factory():
    """Test recovery when no factory is registered."""
    rm = RecoveryManager()
    agent = rm.recover("con_1", "con", {})
    assert agent is None


def test_recovery_manager_factory_failure():
    """Test recovery when the factory raises an exception."""
    rm = RecoveryManager()

    def failing_factory(agent_id, state):
        raise RuntimeError("Spawn failed")

    rm.register_factory("con", failing_factory)
    agent = rm.recover("con_1", "con", {})
    assert agent is None


@pytest.fixture
def watchdog_config() -> Dict[str, Any]:
    """Provide a mock configuration for the watchdog."""
    return {
        "watchdog": {
            "timeout_seconds": 0.2,
            "check_interval_seconds": 0.05
        }
    }


def test_watchdog_triggers_recovery_callback(watchdog_config):
    """Test that Watchdog calls the recovery callback on timeout."""
    recovery_mock = MagicMock()
    wd = Watchdog(watchdog_config, on_timeout=recovery_mock)

    try:
        # Register a fake agent and start
        wd.register_agent("stalled_agent", 99999) # Non-existent PID
        wd.start()

        # Wait for timeout detection
        time.sleep(0.4)

        # Verify callback was triggered
        recovery_mock.assert_called_once_with("stalled_agent", 99999)
    finally:
        wd.stop()


def test_watchdog_no_callback_no_crash(watchdog_config):
    """Test that Watchdog works fine without a callback."""
    wd = Watchdog(watchdog_config, on_timeout=None)
    try:
        wd.register_agent("stalled_agent", 88888)
        wd.start()
        time.sleep(0.4)
        # Should not crash
    finally:
        wd.stop()
