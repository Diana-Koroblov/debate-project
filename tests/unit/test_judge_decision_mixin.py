import json
from unittest.mock import MagicMock

import pytest

from debate_sdk.services.judge_decision_mixin import JudgeDecisionMixin


class _JudgeHarness(JudgeDecisionMixin):
    def __init__(self, outputs):
        self._outputs = iter(outputs)
        self.logger = MagicMock()
        self.topic = "Whether microbes exist on Europa?"

    def generate_argument(self, prompt: str) -> str:
        return next(self._outputs)


def test_evaluate_debate_normalizes_tie_score_and_returns_structured_judgment():
    payload = json.dumps(
        {
            "winner_id": "pro_agent",
            "differential_score": 0,
            "justification": [{"point": "Evidence", "evidence": "Used citations."}],
        }
    )
    judge = _JudgeHarness([payload])

    result = judge.evaluate_debate(["pro: cited data", "con: rebuttal"])

    assert result.winner_id == "pro_agent"
    assert result.differential_score == 0.1
    assert result.justification[0].point == "Evidence"


def test_evaluate_debate_falls_back_after_three_invalid_outputs():
    judge = _JudgeHarness(["not json", json.dumps({}), json.dumps({"winner_id": "unknown"})])

    result = judge.evaluate_debate(["history"])

    assert result.winner_id in {"pro_agent", "con_agent"}
    assert result.differential_score == 0.1
    assert result.justification[0].point == "System Recovery"


def test_normalize_winner_id_infers_side_and_raises_for_unknown_values():
    judge = _JudgeHarness([])

    assert judge._normalize_winner_id({"winner": "Con side"}) == "con_agent"
    assert judge._normalize_winner_id({"justification": ["Pro debater was stronger"]}) == "pro_agent"
    with pytest.raises(ValueError, match="recognizable winner"):
        judge._normalize_winner_id({"winner_id": "ambiguous"})


def test_normalize_justifications_handles_strings_lists_and_non_lists():
    judge = _JudgeHarness([])

    from_string = judge._normalize_justifications("Point A: detail\n- loose line")
    assert from_string == [
        {"point": "Point A", "evidence": "detail"},
        {"point": "Reason 2", "evidence": "loose line"},
    ]

    from_list = judge._normalize_justifications([
        {"text": "Compact reason"},
        "Named point: support",
        "",
    ])
    assert from_list == [
        {"point": "Reason 1", "evidence": "Compact reason"},
        {"point": "Named point", "evidence": "support"},
    ]
    assert judge._normalize_justifications(None) == []


def test_neutral_fallback_uses_topic_when_history_is_empty_and_is_deterministic():
    judge = _JudgeHarness([])

    first = judge._neutral_fallback_winner([])
    second = judge._neutral_fallback_winner([])

    assert first == second
    assert first in {"pro_agent", "con_agent"}