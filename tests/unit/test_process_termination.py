"""Unit tests for process termination and graceful interruption."""

from __future__ import annotations

import contextlib
import multiprocessing
import signal
import time
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest

from debate_sdk.shared.process_utils import is_process_alive, terminate_process_tree
from debate_sdk.shared.watchdog import Watchdog


def dummy_process_func():
    """A process that just sleeps indefinitely."""
    while True:
        time.sleep(1)


def dummy_ignorant_process():
    """A process that ignores SIGTERM."""
    # Note: On Windows, SIGTERM is not catchable/ignorable in the same way as Unix,
    # but we can at least test the logic flow.
    with contextlib.suppress(ValueError, AttributeError):
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
    while True:
        time.sleep(1)


@pytest.fixture
def watchdog_config() -> Dict[str, Any]:
    """Provide a mock configuration for the watchdog."""
    return {
        "watchdog": {
            "timeout_seconds": 0.5,
            "check_interval_seconds": 0.1
        }
    }


def test_terminate_process_tree():
    """Test that terminate_process_tree correctly kills a process."""
    p = multiprocessing.Process(target=dummy_process_func)
    p.start()
    pid = p.pid
    assert is_process_alive(pid)

    success = terminate_process_tree(pid)
    assert success is True
    assert not is_process_alive(pid)
    p.join(timeout=1.0)


def test_watchdog_triggers_termination(watchdog_config, caplog):
    """Test that Watchdog kills a stalled process and cleans up."""
    wd = Watchdog(watchdog_config)
    try:
        p = multiprocessing.Process(target=dummy_process_func)
        p.start()
        pid = p.pid

        wd.register_agent("stalled_agent", pid)
        wd.start()

        # Wait for watchdog to detect timeout and kill
        time.sleep(1.0)

        assert not is_process_alive(pid)
        assert "STALL DETECTED" in caplog.text
        assert "TERMINATION SUCCESS" in caplog.text

        # Verify cleanup
        assert "stalled_agent" not in wd.registry
        assert pid not in wd.heartbeats
    finally:
        wd.stop()
        if p.is_alive():
            p.terminate()
            p.join()


def test_terminate_process_tree_ignorant():
    """Test that terminate_process_tree uses SIGKILL if SIGTERM fails."""
    p = multiprocessing.Process(target=dummy_ignorant_process)
    p.start()
    pid = p.pid

    # Use a very short timeout to trigger the 'alive' logic
    success = terminate_process_tree(pid, timeout=0.1)
    assert success is True
    assert not is_process_alive(pid)
    p.join(timeout=1.0)


def test_terminate_process_tree_failure():
    """Test the failure path when a process cannot be killed."""
    with patch("psutil.Process") as mock_process_cls:
        mock_parent = MagicMock()
        mock_process_cls.return_value = mock_parent
        mock_parent.children.return_value = []

        # Mock wait_procs to always return the process as alive
        with patch("psutil.wait_procs") as mock_wait:
            mock_wait.return_value = ([], [mock_parent])

            success = terminate_process_tree(1234, timeout=0.1)
            assert success is False


def test_is_process_alive_non_existent():
    """Test is_process_alive with a non-existent PID."""
    # Assuming PID 999999 is unlikely to exist
    assert not is_process_alive(999999)
