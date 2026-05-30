"""Orchestrator Process (ParentJudgeAgent) for the debate swarm."""

from __future__ import annotations

import json
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

        debate_cfg = config.setdefault("debate", {})
        GroqMixin.__init__(
            self, model_name=debate_cfg.get("model", "openai/gpt-oss-20b"),
            system_instruction="You are the Supreme Judge of the Scientific Debate.",
            generation_config={
                "response_mime_type": "application/json",
                "max_completion_tokens": 768,
            }
        )
        self.topic = self._decide_topic(debate_cfg)
        self._apply_topic_personas(debate_cfg, self.topic)
        self.current_round = 0
        self.max_rounds = int(debate_cfg.get("rounds", 10))
        self.active_agent_id: str | None = None
        self.watchdog = Watchdog(config)
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

    def _decide_topic(self, debate_cfg: Dict[str, Any]) -> str:
        """Generate a fresh topic for the session using the parent model."""
        topic_prompt = (
            "Generate one scientific debate topic for two agents.\n"
            "Requirements:\n"
            "1. Topic must be a genuinely unresolved or actively contested scientific question.\n"
            "2. There must be credible evidence or expert arguments available for both pro and con sides.\n"
            "3. Avoid questions where current mainstream evidence overwhelmingly settles the answer in one direction.\n"
            "4. Phrase the topic neutrally as a question beginning with Whether, Does, Should, Can, Is, or Are.\n"
            "5. Keep it to one sentence, 8-18 words.\n"
            "6. No markdown and no quotes.\n"
            "Return valid JSON only: {\"topic\": \"...\", \"balance_rationale\": \"one short sentence\"}"
        )

        last_error: Exception | None = None
        for attempt in range(3):
            try:
                raw_output = getattr(self, "generate_argument")(topic_prompt)
                parsed = json.loads(raw_output)
                topic = self._normalize_generated_topic(str(parsed.get("topic", "")).strip())
                balance_rationale = str(parsed.get("balance_rationale", "")).strip()
                if not topic or not balance_rationale:
                    raise ValueError("Topic generator did not return a valid balanced topic payload")

                if self._is_actively_contested_topic(topic, balance_rationale):
                    return topic
                raise ValueError("Topic validator rejected candidate as insufficiently contested")
            except Exception as exc:
                last_error = exc
                self.logger.warning(
                    "Topic generation attempt %s failed: %s",
                    attempt + 1,
                    exc,
                )

        raise RuntimeError(
            "Judge failed to generate an actively contested scientific topic"
        ) from last_error

    def _normalize_generated_topic(self, topic: str) -> str:
        """Accept only neutral question-shaped generated topics."""
        cleaned = topic.strip().strip('"').rstrip(". ")
        if not cleaned:
            return ""

        allowed_starts = ("whether", "does", "should", "can", "is", "are")
        if not cleaned.lower().startswith(allowed_starts):
            return ""

        if not cleaned.endswith("?"):
            cleaned += "?"
        return cleaned

    def _is_actively_contested_topic(self, topic: str, balance_rationale: str) -> bool:
        """Ask the judge model to verify that a candidate topic is genuinely contested."""
        validation_prompt = (
            "Evaluate whether this scientific debate topic is actively contested.\n"
            f"Topic: {topic}\n"
            f"Balance rationale: {balance_rationale}\n"
            "Accept only if both sides have credible evidence or expert arguments and the answer is not overwhelmingly settled by mainstream evidence.\n"
            "Return valid JSON only: {\"accepted\": true or false, \"reason\": \"one short sentence\"}"
        )
        raw_output = getattr(self, "generate_argument")(validation_prompt)
        parsed = json.loads(raw_output)
        if bool(parsed.get("accepted")):
            return True

        reason = str(parsed.get("reason", "validator rejected topic")).strip()
        self.logger.info("Topic validator rejected candidate: %s", reason)
        return False

    def _apply_topic_personas(self, debate_cfg: Dict[str, Any], topic: str) -> None:
        """Bind the selected topic into child-agent personas for this run."""
        persona = (
            f"{topic}. Stay evidence-based, answer the opponent directly, "
            "and keep each turn concise."
        )
        debate_cfg["topic"] = topic
        debate_cfg["pro_persona"] = persona
        debate_cfg["con_persona"] = persona
