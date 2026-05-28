"""Orchestrator Process (ParentJudgeAgent) for the debate swarm."""

from __future__ import annotations

import multiprocessing
from typing import Any, Dict

from debate_sdk.services.base_agent import BaseAgent
from debate_sdk.services.groq_mixin import GroqMixin
from debate_sdk.services.judge_decision_mixin import JudgeDecisionMixin
from debate_sdk.services.judge_process_mixin import JudgeProcessMixin
from debate_sdk.services.judge_routing_mixin import JudgeRoutingMixin
from debate_sdk.shared.contracts import (
    ChildToParentMessage,
    JudgmentJustification,
    TokenTelemetry,
)
from debate_sdk.shared.exceptions import BudgetExceededException
from debate_sdk.shared.history import HistoryLedger
from debate_sdk.shared.state_manager import StateManager
from debate_sdk.shared.watchdog import Watchdog


class ParentJudgeAgent(
    BaseAgent, GroqMixin, JudgeProcessMixin, JudgeDecisionMixin, JudgeRoutingMixin
):
    """Centralized authority process that orchestrates the debate."""

    def __init__(
        self,
        agent_id: str,
        config: Dict[str, Any],
        inbound_queue: multiprocessing.Queue,
        outbound_queue: multiprocessing.Queue
    ) -> None:
        """Initialize the judge, its queues, and its orchestration state."""
        super().__init__(agent_id, config, inbound_queue, outbound_queue)
        JudgeProcessMixin.__init__(self)
        JudgeDecisionMixin.__init__(self)

        self.pro_inbound: multiprocessing.Queue = multiprocessing.Queue()
        self.con_inbound: multiprocessing.Queue = multiprocessing.Queue()

        debate_cfg = config.get("debate", {})
        self.current_round = 0
        self.max_rounds = int(debate_cfg.get("rounds", 10))
        self.active_agent_id: str | None = None
        self.watchdog = Watchdog(config)
        GroqMixin.__init__(
            self, model_name=debate_cfg.get("model", "llama-3.1-8b-instant"),
            system_instruction="You are the Supreme Judge of the Scientific Debate.",
            generation_config={
                "response_mime_type": "application/json",
                "max_completion_tokens": 768,
            }
        )
        self.ledger = HistoryLedger()
        self.state_manager = StateManager(
            config.get("storage_dir", "results/state"),
            config.get("session_id", "default"),
        )

    def handle_message(self, message: Any) -> None:
        """6.3.2: Deterministic routing and turn management."""
        self._update_heartbeat(message)

        if isinstance(message, TokenTelemetry):
            self.send_message(message.model_dump())
            return

        if isinstance(message, ChildToParentMessage):
            if message.agent_id != self.active_agent_id:
                self.logger.warning(f"Ignored out-of-turn message from '{message.agent_id}'")
                return

            self.logger.info(f"Argument received: {message.agent_id} | Round {self.current_round}")
            if self.config.get("stream_events", False):
                self.send_message(message.model_dump())
            self.ledger.add_entry(message)
            self._backup_state()
            self._route_next_turn()

    def _backup_state(self) -> None:
        """Flush the current ledger and state to disk."""
        state = {"ledger": self.ledger.to_list(), "round": self.current_round}
        self.state_manager.save_state(state)

    def run(self) -> None:
        """Run the judge loop with budget-failure handling."""
        try:
            super().run()
        except BudgetExceededException:
            self._handle_budget_failure()
        except Exception as exc:
            self.logger.error(f"Judge process failed: {exc}")
            self.terminate()

    def _handle_budget_failure(self) -> None:
        """Halt child processes and deliver a partial-history judgment."""
        self.logger.error("SYSTEM RESOURCE DEPLETED: Token budget exceeded.")
        self.terminate_children()
        self.active_agent_id = None
        self.logger.info("Executing graceful degradation: Partial history judgment.")
        partial_history = self.ledger.get_full_history_strings()
        judgment = self.evaluate_debate(partial_history)
        judgment.justification.insert(0, JudgmentJustification(
            point="RESOURCE_TRUNCATION",
            evidence=f"Debate halted at round {self.current_round} due to budget exhaustion."
        ))
        self.send_message(judgment.model_dump())
        self.logger.info(f"TRUNCATED WINNER DECLARED: {judgment.winner_id}")
        self.terminate()
