"""Mixin for turn-based routing and heartbeat management in ParentJudgeAgent."""

from __future__ import annotations

from typing import Any

from debate_sdk.shared.contracts import ParentToChildRouter


class JudgeRoutingMixin:
    """
    Handles turn-based routing, prompt construction, and agent heartbeats.
    """

    def start_debate(self) -> None:
        """Initiate the first round by prompting the Pro agent."""
        topic = str(getattr(self, "topic", "")).strip() or str(
            self.config.get("debate", {}).get("topic", "")
        ).strip()
        if topic:
            self.send_message({"type": "topic_selected", "topic": topic})

        self.logger.info("DEBATE START: Round 1, Pro agent.")
        self.current_round = 1
        self._send_turn_prompt("pro_agent")

    def _send_turn_prompt(self, agent_id: str) -> None:
        """6.3.3: Construct and route the ParentToChildRouter contract."""
        self.active_agent_id = agent_id
        is_last = self.current_round >= self.max_rounds and agent_id == "con_agent"

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
            if self.current_round < self.max_rounds:
                self.current_round += 1
                self._send_turn_prompt("pro_agent")
            else:
                self.logger.info(
                    "Debate concluded after %s rounds. Finalizing judgment...",
                    self.max_rounds,
                )
                self.active_agent_id = None
                self.terminate_children()
                final_history = self.ledger.get_full_history_strings()
                judgment = self.evaluate_debate(final_history)
                self.send_message(judgment.model_dump())
                self.logger.info(f"WINNER DECLARED: {judgment.winner_id}")

    def _update_heartbeat(self, message: Any) -> None:
        """6.3.4: Verify agent activity and update watchdog."""
        agent_id = getattr(message, "agent_id", None)
        if agent_id:
            pid = self.pro_process.pid if agent_id == "pro_agent" else self.con_process.pid
            self.watchdog.heartbeat(pid)
