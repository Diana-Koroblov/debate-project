"""Mixin for final judging logic and tie-breaking protocols."""

from __future__ import annotations

import hashlib
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

        last_error: Exception | None = None
        for attempt in range(3):
            try:
                raw_output = getattr(self, "generate_argument")(eval_prompt)
                data = self._normalize_judgment_payload(json.loads(raw_output))
                judgment = FinalJudgmentSchema(**data)

                if judgment.differential_score == 0:
                    self.logger.warning("Judge attempted a tie. Preserving winner and using minimum score.")
                    judgment.differential_score = 0.1

                return judgment
            except (json.JSONDecodeError, Exception) as exc:
                last_error = exc
                self.logger.warning(
                    "Judging attempt %s failed: %s",
                    attempt + 1,
                    exc,
                )

        fallback_winner = self._neutral_fallback_winner(history)
        self.logger.error("Judging failure after retries; using neutral fallback winner %s", fallback_winner)
        return FinalJudgmentSchema(
            winner_id=fallback_winner,
            differential_score=0.1,
            justification=[{
                "point": "System Recovery",
                "evidence": str(last_error or "Judge output remained invalid after retries."),
            }],
        )

    def _normalize_judgment_payload(self, data: dict[str, Any]) -> dict[str, Any]:
        """Coerce common model formatting mistakes into the expected schema."""
        normalized = dict(data)

        normalized["winner_id"] = self._normalize_winner_id(normalized)

        try:
            score = float(normalized.get("differential_score", 1.0))
        except (TypeError, ValueError):
            score = 1.0
        normalized["differential_score"] = abs(score) or 0.1

        normalized["justification"] = self._normalize_justifications(
            normalized.get("justification", [])
        )
        return normalized

    def _normalize_winner_id(self, data: dict[str, Any]) -> str:
        """Normalize a winner id without defaulting malformed values to one side."""
        winner_id = str(data.get("winner_id") or data.get("winner") or "").strip()
        winner_lower = winner_id.lower()
        if winner_lower in {"pro_agent", "con_agent"}:
            return winner_lower
        if "con" in winner_lower and "pro" not in winner_lower:
            return "con_agent"
        if "pro" in winner_lower and "con" not in winner_lower:
            return "pro_agent"

        inferred = self._infer_winner_from_justifications(data.get("justification", []))
        if inferred:
            return inferred

        raise ValueError("Judge output did not specify a recognizable winner")

    def _infer_winner_from_justifications(self, value: Any) -> str | None:
        """Infer the intended winner from justification text when the winner field is malformed."""
        haystack = json.dumps(value, ensure_ascii=True).lower()
        has_pro = any(token in haystack for token in ("pro_agent", "pro side", "pro debater"))
        has_con = any(token in haystack for token in ("con_agent", "con side", "con debater"))
        if has_pro and not has_con:
            return "pro_agent"
        if has_con and not has_pro:
            return "con_agent"
        return None

    def _neutral_fallback_winner(self, history: List[str]) -> str:
        """Pick a deterministic recovery winner without always favoring one side."""
        seed = "\n".join(history).strip()
        if not seed:
            seed = str(getattr(self, "topic", "judge-fallback"))
        digest = hashlib.sha256(seed.encode("utf-8")).digest()
        return "pro_agent" if digest[0] % 2 == 0 else "con_agent"

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
