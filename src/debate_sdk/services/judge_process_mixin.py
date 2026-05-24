"""Mixin for managing child debater processes within the ParentJudgeAgent."""

from __future__ import annotations

import multiprocessing
from typing import Any, Dict

from debate_sdk.services.base_agent import BaseAgent
from debate_sdk.services.con_agent import ConDebaterAgent
from debate_sdk.services.pro_agent import ProDebaterAgent
from debate_sdk.shared.process_utils import terminate_process_tree


def _agent_worker(
    agent_cls: type[BaseAgent],
    agent_id: str,
    config: Dict[str, Any],
    inbound: multiprocessing.Queue,
    outbound: multiprocessing.Queue
) -> None:
    """Standalone worker function to run an agent in a separate process."""
    agent = agent_cls(agent_id, config, inbound, outbound)
    agent.run()


class JudgeProcessMixin:
    """
    Handles the lifecycle of child debater processes.
    """

    def __init__(self) -> None:
        """Initialize process tracking attributes."""
        self.pro_process: multiprocessing.Process | None = None
        self.con_process: multiprocessing.Process | None = None
        # Queues are initialized in ParentJudgeAgent.__init__

    def spawn_children(
        self,
        pro_cls: type[BaseAgent] = ProDebaterAgent,
        con_cls: type[BaseAgent] = ConDebaterAgent
    ) -> None:
        """6.1.4: Launch, track, and manage child worker processes."""
        # Use Judge's inbound_queue as children's outbound_queue for routing
        args_pro = (pro_cls, "pro_agent", self.config, self.pro_inbound, self.inbound_queue)
        self.pro_process = multiprocessing.Process(
            target=_agent_worker, args=args_pro, name="ProDebater", daemon=True
        )

        args_con = (con_cls, "con_agent", self.config, self.con_inbound, self.inbound_queue)
        self.con_process = multiprocessing.Process(
            target=_agent_worker, args=args_con, name="ConDebater", daemon=True
        )

        self.pro_process.start()
        self.con_process.start()

        # Register with watchdog
        getattr(self, "watchdog").register_agent("pro_agent", self.pro_process.pid)
        getattr(self, "watchdog").register_agent("con_agent", self.con_process.pid)
        getattr(self, "watchdog").start()

    def terminate_children(self) -> None:
        """Gracefully shut down all managed child processes."""
        for proc in [self.pro_process, self.con_process]:
            if proc and proc.pid:
                terminate_process_tree(proc.pid)
        getattr(self, "watchdog").stop()
