"""Watchdog daemon for monitoring agent process health."""

from __future__ import annotations

import threading
import time
from multiprocessing import Manager
from typing import Any, Callable, Dict

from debate_sdk.shared.logger import setup_logger
from debate_sdk.shared.process_utils import terminate_process_tree

logger = setup_logger("watchdog")


class Watchdog:
    """
    Monitors agent processes and detects stalls via heartbeat signals.

    Attributes:
        timeout (float): Seconds before a process is considered stalled.
        interval (float): Seconds between health checks.
        registry (Dict[str, int]): Shared map of agent_id to PID.
        heartbeats (Dict[int, float]): Shared map of PID to last heartbeat timestamp.
        on_timeout (Callable[[str, int], None] | None): Callback for recovery.
    """

    def __init__(
        self,
        config: Dict[str, Any],
        on_timeout: Callable[[str, int], None] | None = None
    ) -> None:
        """
        Initialize the Watchdog with configuration parameters.

        Args:
            config (Dict[str, Any]): Setup configuration dictionary.
            on_timeout (Callable[[str, int], None] | None): Recovery callback.
        """
        self.timeout = config["watchdog"]["timeout_seconds"]
        self.interval = config["watchdog"]["check_interval_seconds"]
        self.on_timeout = on_timeout

        self._manager = Manager()
        self.registry: Dict[str, int] = self._manager.dict()
        self.heartbeats: Dict[int, float] = self._manager.dict()
        self._processes: Dict[str, Any] = {}

        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def register_agent(self, agent_id: str, proc_or_pid: Any) -> None:
        """
        Register a new agent process for monitoring.

        Args:
            agent_id (str): Unique identifier for the agent.
            proc_or_pid (multiprocessing.Process | int): Process object or PID.
        """
        if hasattr(proc_or_pid, "pid"):
            pid = proc_or_pid.pid
            self._processes[agent_id] = proc_or_pid
        else:
            pid = int(proc_or_pid)

        self.registry[agent_id] = pid
        self.heartbeat(pid)
        logger.info(f"Registered agent '{agent_id}' with PID {pid}")

    def unregister_agent(self, agent_id: str) -> None:
        """
        Remove an agent from monitoring.

        Args:
            agent_id (str): Unique identifier of the agent to remove.
        """
        pid = self.registry.pop(agent_id, None)
        if pid:
            self.heartbeats.pop(pid, None)
            logger.info(f"Unregistered agent '{agent_id}' (PID {pid})")

    def heartbeat(self, pid: int) -> None:
        """
        Update the heartbeat timestamp for a specific process.

        Args:
            pid (int): OS Process ID of the agent.
        """
        self.heartbeats[pid] = time.time()

    def start(self) -> None:
        """Launch the watchdog monitoring loop in a background thread."""
        if self._thread and self._thread.is_alive():
            return

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        logger.info("Watchdog daemon started")

    def stop(self) -> None:
        """Gracefully terminate the watchdog monitoring thread and manager."""
        self._stop_event.set()
        if self._thread:
            self._thread.join()
        self._manager.shutdown()
        logger.info("Watchdog daemon stopped")

    def _run_loop(self) -> None:
        """Internal periodic loop checking for timed-out heartbeats."""
        while not self._stop_event.is_set():
            now = time.time()
            # Convert to list to avoid runtime dict mutation errors during iteration
            for agent_id, pid in list(self.registry.items()):
                last_hb = self.heartbeats.get(pid, 0.0)
                if now - last_hb > self.timeout:
                    self._on_timeout(agent_id, pid)

            time.sleep(self.interval)

    def _on_timeout(self, agent_id: str, pid: int) -> None:
        """
        Triggered when an agent exceeds its heartbeat timeout threshold.

        Args:
            agent_id (str): Identity of the stalled agent.
            pid (int): PID of the stalled agent.
        """
        logger.error(
            f"STALL DETECTED: Agent '{agent_id}' (PID {pid}) failed heartbeat! "
            f"Forcing termination sequence."
        )

        import contextlib
        success = terminate_process_tree(pid)
        proc = self._processes.pop(agent_id, None)
        if proc and hasattr(proc, "join"):
            with contextlib.suppress(Exception):
                proc.join(timeout=2.0)

        if success:
            logger.info(f"TERMINATION SUCCESS: Agent '{agent_id}' (PID {pid}) killed.")
        else:
            logger.warning(f"TERMINATION INCOMPLETE: Some remnants of PID {pid} may exist.")

        # Cleanup registry and heartbeats to prevent repeat triggers or zombie tracking
        self.registry.pop(agent_id, None)
        self.heartbeats.pop(pid, None)

        # Trigger recovery callback
        if self.on_timeout:
            self.on_timeout(agent_id, pid)
