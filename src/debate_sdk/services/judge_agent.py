"""Orchestrator Process (ParentJudgeAgent) for the debate swarm."""

from __future__ import annotations

import multiprocessing
from datetime import datetime
from typing import Any, Dict

from debate_sdk.services.base_agent import BaseAgent
from debate_sdk.services.gemini_mixin import GeminiMixin
from debate_sdk.services.judge_decision_mixin import JudgeDecisionMixin
from debate_sdk.services.judge_process_mixin import JudgeProcessMixin
from debate_sdk.shared.contracts import (
    ChildToParentMessage,
    FinalJudgmentSchema,
    HeartbeatMessage,
    JudgmentJustification,
    ParentToChildRouter,
    TokenTelemetry,
)
from debate_sdk.shared.exceptions import BudgetExceededException
from debate_sdk.shared.history import HistoryLedger
from debate_sdk.shared.state_manager import StateManager
from debate_sdk.shared.watchdog import Watchdog


class ParentJudgeAgent(BaseAgent, GeminiMixin, JudgeProcessMixin, JudgeDecisionMixin):
    """
    Centralized authority process that orchestrates the debate.
    """

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

        # 6.3.1: Strict round tracking (exactly 10 rounds)
        self.current_round = 0
        self.active_agent_id: str | None = None
        self.watchdog = Watchdog(config)

        # Mixin & Shared state initialization
        debate_cfg = config.get("debate", {})
        GeminiMixin.__init__(
            self, model_name=debate_cfg.get("model", "gemini-1.5-pro"),
            system_instruction="You are the Supreme Judge of the Scientific Debate.",
            generation_config={"response_mime_type": "application/json"}
        )
        self.ledger = HistoryLedger()
        self.state_manager = StateManager(config.get("storage_dir", "results/state"), 
                                        config.get("session_id", "default"))

    def start_debate(self) -> None:
        """Initiate the first round by prompting the Pro agent."""
        self.logger.info("DEBATE START: Round 1, Pro agent.")
        self.current_round = 1
        self._send_turn_prompt("pro_agent")

    def handle_message(self, message: Any) -> None:
        """6.3.2: Deterministic routing and turn management."""
        self._update_heartbeat(message)

        if isinstance(message, ChildToParentMessage):
            if message.agent_id != self.active_agent_id:
                self.logger.warning(f"Ignored out-of-turn message from '{message.agent_id}'")
                return

            self.logger.info(f"Argument received: {message.agent_id} | Round {self.current_round}")
            self.ledger.add_entry(message)
            self._backup_state()
            self._route_next_turn()

    def _send_turn_prompt(self, agent_id: str) -> None:
        """6.3.3: Construct and route the ParentToChildRouter contract."""
        self.active_agent_id = agent_id
        is_last = self.current_round >= 10 and agent_id == "con_agent"
        
        prompt = ParentToChildRouter(
            recipient_id=agent_id,
            history=self.ledger.get_full_history_strings(),
            game_status="ENDING" if is_last else "ACTIVE"
        )
        
        target = self.pro_inbound if agent_id == "pro_agent" else self.con_inbound
        target.put(prompt.model_dump())

    def _route_next_turn(self) -> None:
        """Determine and trigger the next player or judge phase."""
        if self.active_agent_id == "pro_agent":
            self._send_turn_prompt("con_agent")
        else:
            if self.current_round < 10:
                self.current_round += 1
                self._send_turn_prompt("pro_agent")
            else:
                self.logger.info("Debate concluded after 10 rounds. Finalizing judgment...")
                self.active_agent_id = None
                
                # 6.4: Execute judging phase
                final_history = self.ledger.get_full_history_strings()
                judgment = self.evaluate_debate(final_history)
                
                # Emit the final judgment
                self.send_message(judgment.model_dump())
                self.logger.info(f"WINNER DECLARED: {judgment.winner_id}")

    def _update_heartbeat(self, message: Any) -> None:
        """6.3.4: Verify agent activity and update watchdog."""
        agent_id = getattr(message, "agent_id", None)
        if agent_id:
            pid = self.pro_process.pid if agent_id == "pro_agent" else self.con_process.pid
            self.watchdog.heartbeat(pid)

    def _backup_state(self) -> None:
        """Flush the current ledger and state to disk."""
        state = {"ledger": self.ledger.to_list(), "round": self.current_round}
        self.state_manager.save_state(state)

    def run(self) -> None:
        """
        6.5.1: Enclose the orchestration loop in a BudgetExceededException block.
        """
        try:
            super().run()
        except BudgetExceededException:
            self._handle_budget_failure()
        except Exception as exc:
            self.logger.error(f"Judge process failed: {exc}")
            self.terminate()

    def _handle_budget_failure(self) -> None:
        """
        6.5.2: Halt child processes and deliver fallback judgment.
        """
        self.logger.error("SYSTEM RESOURCE DEPLETED: Token budget exceeded.")
        
        # Immediate halt of child processes
        self.terminate_children()
        self.active_agent_id = None

        # 6.5.3: Fallback evaluation via partial history
        self.logger.info("Executing graceful degradation: Partial history judgment.")
        
        partial_history = self.ledger.get_full_history_strings()
        judgment = self.evaluate_debate(partial_history)
        
        # 6.5.4: Force the judge to acknowledge truncation in justifications
        judgment.justification.insert(0, JudgmentJustification(
            point="RESOURCE_TRUNCATION",
            evidence=f"Debate halted at round {self.current_round} due to budget exhaustion."
        ))

        self.send_message(judgment.model_dump())
        self.logger.info(f"TRUNCATED WINNER DECLARED: {judgment.winner_id}")
        self.terminate()
