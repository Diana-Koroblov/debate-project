"""Mixin for final judging logic and tie-breaking protocols."""

from __future__ import annotations

import json
from typing import Any, List

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
            data = self._normalize_judgment_payload(json.loads(raw_output))
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

    def _normalize_judgment_payload(self, data: dict[str, Any]) -> dict[str, Any]:
        """Coerce common model formatting mistakes into the expected schema."""
        normalized = dict(data)

        winner_id = str(normalized.get("winner_id") or normalized.get("winner") or "").strip()
        winner_lower = winner_id.lower()
        if winner_lower not in {"pro_agent", "con_agent"}:
            if "con" in winner_lower:
                winner_id = "con_agent"
            else:
                winner_id = "pro_agent"
        normalized["winner_id"] = winner_id

        try:
            score = float(normalized.get("differential_score", 1.0))
        except (TypeError, ValueError):
            score = 1.0
        normalized["differential_score"] = abs(score) or 0.1

        normalized["justification"] = self._normalize_justifications(
            normalized.get("justification", [])
        )
        return normalized

    def _normalize_justifications(self, value: Any) -> list[dict[str, str]]:
        """Convert free-form or partially structured justifications into schema shape."""
        if isinstance(value, str):
            raw_items: list[Any] = [line.strip(" -*") for line in value.splitlines() if line.strip()]
        elif isinstance(value, list):
            raw_items = value
        else:
            raw_items = []

        normalized: list[dict[str, str]] = []
        for index, item in enumerate(raw_items, start=1):
            if isinstance(item, dict):
                point = str(item.get("point") or f"Reason {index}").strip()
                evidence = str(
                    item.get("evidence") or item.get("text") or item.get("reason") or ""
                ).strip()
            else:
                cleaned = str(item).strip()
                if not cleaned:
                    continue
                if ":" in cleaned:
                    point, evidence = cleaned.split(":", 1)
                    point = point.strip() or f"Reason {index}"
                    evidence = evidence.strip()
                else:
                    point = f"Reason {index}"
                    evidence = cleaned

            if point or evidence:
                normalized.append({"point": point, "evidence": evidence})

        return normalized

    def _build_evaluation_prompt(self, history: List[str]) -> str:
        """Construct the prompt for the judging engine."""
        history_text = "\n".join(history)
        return (
            f"DEBATE HISTORY:\n{history_text}\n\n"
            "INSTRUCTIONS FOR THE SUPREME JUDGE:\n"
            "1. Decide which side was more scientifically correct overall.\n"
            "2. Reward factual accuracy, evidential support, and direct rebuttals of the opponent.\n"
            "3. Penalize unsupported speculation, factual mistakes, and failure to address the latest rebuttal.\n"
            "4. ANTI-TIE PROTOCOL: You MUST declare exactly one winner. A tie is a failure.\n"
            "5. Assign a non-zero differential score between 1 and 10 representing the margin of correctness.\n"
            "6. Provide 2 or 3 short justification items.\n"
            "7. Output MUST be valid JSON with exactly these keys: "
            "\"winner_id\", \"differential_score\", and \"justification\".\n"
            "8. The justification value MUST be a JSON array of objects shaped like "
            "{\"point\": \"short label\", \"evidence\": \"short explanation\"}."
        )
