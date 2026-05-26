"""Mixin for final judging logic and tie-breaking protocols."""

from __future__ import annotations

import json
from typing import List

from debate_sdk.shared.contracts import FinalJudgmentSchema


class JudgeDecisionMixin:
    """
    Handles the final evaluation of the debate history.
    """

    def evaluate_debate(self, history: List[str]) -> FinalJudgmentSchema:
        """
        6.4.1: Grade based on persuasiveness, rhetoric, and rules.
        6.4.2: Enforce "Anti-Tie Protocol".
        """
        self.logger.info("Supreme Judge is evaluating the final arguments...")

        # 6.4.1 & 6.4.2: Formulate the unyielding "No-Tie" prompt
        eval_prompt = self._build_evaluation_prompt(history)

        # 1. Generation (JSON output enforced by Mixin config)
        raw_output = getattr(self, "generate_argument")(eval_prompt)

        try:
            data = json.loads(raw_output)
            # 6.4.3: Extract and validate via FinalJudgmentSchema
            judgment = FinalJudgmentSchema(**data)

            # Outlaw ties (differential_score must be non-zero)
            if judgment.differential_score == 0:
                self.logger.warning("Judge attempted a tie. Forcing re-evaluation.")
                judgment.differential_score = 0.1 # Minimal bias for Pro if tied

            return judgment
        except (json.JSONDecodeError, Exception) as exc:
            self.logger.error(f"Judging failure: {exc}")
            # Fallback judgment
            return FinalJudgmentSchema(
                winner_id="pro_agent",
                differential_score=1.0,
                justification=[{"point": "System Error", "evidence": str(exc)}]
            )

    def _build_evaluation_prompt(self, history: List[str]) -> str:
        """Construct the prompt for the judging engine."""
        history_text = "\n".join(history)
        return (
            f"DEBATE HISTORY:\n{history_text}\n\n"
            "INSTRUCTIONS FOR THE SUPREME JUDGE:\n"
            "1. Evaluate the entire debate based on rhetoric and scientific persuasiveness.\n"
            "2. Ignore absolute factual truth; focus on who argued their stance better.\n"
            "3. ANTI-TIE PROTOCOL: You MUST declare a winner. A tie is a failure.\n"
            "4. Assign a differential score between 1 and 10 representing the margin of victory.\n"
            "5. Provide granular justifications for your decision.\n"
            "6. Output MUST be valid JSON. You MUST use exactly these keys: "
            "\"winner_id\", \"differential_score\", and \"justification\". "
            "Do NOT use a key named \"winner\"; use \"winner_id\"."
        )
