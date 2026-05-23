"""Unit tests for the Watchdog process monitoring daemon."""

from __future__ import annotations

import time
from typing import Any, Dict

import pytest

from debate_sdk.shared.watchdog import Watchdog


@pytest.fixture
def watchdog_config() -> Dict[str, Any]:
    """Provide a mock configuration for the watchdog."""
    return {
        "watchdog": {
            "timeout_seconds": 0.5,
            "check_interval_seconds": 0.1
        }
    }


def test_watchdog_registration(watchdog_config):
    """Test that agents can be registered with the watchdog."""
    wd = Watchdog(watchdog_config)
    try:
        wd.register_agent("pro_agent", 1234)
        assert wd.registry["pro_agent"] == 1234
        assert 1234 in wd.heartbeats
    finally:
        wd.stop()


def test_watchdog_heartbeat_update(watchdog_config):
    """Test that heartbeats can be updated for registered agents."""
    wd = Watchdog(watchdog_config)
    try:
        wd.register_agent("pro_agent", 1234)
        first_hb = wd.heartbeats[1234]
        time.sleep(0.1)
        wd.heartbeat(1234)
        assert wd.heartbeats[1234] > first_hb
    finally:
        wd.stop()


def test_watchdog_timeout_detection(watchdog_config, caplog):
    """Test that the watchdog detects and logs stalled agents."""
    wd = Watchdog(watchdog_config)
    try:
        wd.register_agent("con_agent", 5678)
        wd.start()

        # Wait for timeout (0.5s timeout + some buffer)
        time.sleep(0.8)

        assert "STALL DETECTED" in caplog.text
        assert "Agent 'con_agent' (PID 5678)" in caplog.text
    finally:
        wd.stop()


def test_watchdog_prevents_timeout_with_heartbeat(watchdog_config, caplog):
    """Test that active heartbeats prevent timeout detection."""
    wd = Watchdog(watchdog_config)
    try:
        wd.register_agent("pro_agent", 1111)
        wd.start()

        # Halfway to timeout, send heartbeat
        time.sleep(0.3)
        wd.heartbeat(1111)

        # Wait more time, total 0.6s > 0.5s timeout, but heartbeat was reset
        time.sleep(0.3)

        assert "STALL DETECTED" not in caplog.text
    finally:
        wd.stop()


def test_watchdog_double_start(watchdog_config):
    """Test that start() is idempotent and doesn't launch multiple threads."""
    wd = Watchdog(watchdog_config)
    try:
        wd.start()
        first_thread = wd._thread
        wd.start()
        assert wd._thread is first_thread
    finally:
        wd.stop()


def test_watchdog_multiple_agents(watchdog_config, caplog):
    """Test monitoring multiple agents simultaneously."""
    wd = Watchdog(watchdog_config)
    try:
        wd.register_agent("agent1", 101)
        wd.register_agent("agent2", 102)
        wd.start()

        # agent1 keeps beating, agent2 stalls
        for _ in range(8):  # Total 0.8s > 0.5s timeout
            time.sleep(0.1)
            wd.heartbeat(101)

        assert "STALL DETECTED" in caplog.text
        assert "Agent 'agent2' (PID 102)" in caplog.text
        assert "Agent 'agent1' (PID 101)" not in caplog.text
    finally:
        wd.stop()
