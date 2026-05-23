"""Integration tests for Watchdog process monitoring and recovery."""

from __future__ import annotations

import multiprocessing
import time
from pathlib import Path
from typing import Any, Dict

import pytest

from debate_sdk.shared.process_utils import is_process_alive, terminate_process_tree
from debate_sdk.shared.recovery import RecoveryManager
from debate_sdk.shared.state_manager import StateManager
from debate_sdk.shared.watchdog import Watchdog


def mock_agent_worker(
    agent_id: str,
    storage_dir: Path,
    shared_results: Dict[str, Any]
) -> None:
    """
    Simulated agent worker for recovery testing.

    If it's the first run, it saves state and hangs.
    If it's a recovered run, it marks success and exits.
    """
    sm = StateManager(storage_dir, "integration_test")
    state = sm.load_state() or {"round": 0}

    if state["round"] == 0:
        # First run: increment state, save, and simulate hang
        state["round"] = 1
        sm.save_state(state)
        # Infinite loop to simulate hang
        while True:
            time.sleep(0.1)
    else:
        # Recovered run: signal success and terminate
        shared_results["recovered_success"] = True
        shared_results["final_round"] = state["round"]


@pytest.fixture
def integration_config() -> Dict[str, Any]:
    """Mock configuration with fast watchdog cycles for integration testing."""
    return {
        "watchdog": {
            "timeout_seconds": 0.5,
            "check_interval_seconds": 0.1
        }
    }


def test_end_to_end_recovery(integration_config, tmp_path, caplog):
    """
    Test the full cycle: spawn -> hang -> detect -> kill -> recover -> finish.
    """
    manager = multiprocessing.Manager()
    shared_results = manager.dict({"recovered_success": False})
    storage_dir = tmp_path / "states"

    rm = RecoveryManager()

    def spawn_factory(agent_id, state):
        p = multiprocessing.Process(
            target=mock_agent_worker,
            args=(agent_id, storage_dir, shared_results)
        )
        p.start()
        wd.register_agent(agent_id, p.pid)
        return p

    rm.register_factory("mock_agent", spawn_factory)

    def on_timeout(agent_id, pid):
        sm = StateManager(storage_dir, "integration_test")
        state = sm.load_state() or {}
        rm.recover(agent_id, "mock_agent", state)

    wd = Watchdog(integration_config, on_timeout=on_timeout)

    try:
        # Start Initial Agent
        p1 = multiprocessing.Process(
            target=mock_agent_worker, args=("agent_1", storage_dir, shared_results)
        )
        p1.start()
        original_pid = p1.pid
        wd.register_agent("agent_1", original_pid)
        wd.start()

        # Wait for recovery (timeout=0.5s)
        time.sleep(1.5)

        assert "STALL DETECTED" in caplog.text
        assert not is_process_alive(original_pid)
        assert shared_results["recovered_success"] is True

    finally:
        # Get PIDs BEFORE stopping manager
        active_pids = list(wd.heartbeats.keys())
        wd.stop()
        for pid in active_pids:
            terminate_process_tree(pid)
        if 'p1' in locals() and p1.is_alive():
            p1.terminate()
            p1.join()
        manager.shutdown()
