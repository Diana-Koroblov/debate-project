"""Tests for gatekeeper budget guardrails and version compliance."""

import pytest

from debate_sdk.shared.exceptions import BudgetExceededException
from debate_sdk.shared.gatekeeper import ApiGatekeeper


def setup_function():
    ApiGatekeeper.reset_instance()


def test_budget_overrun_raises_budget_exceeded_exception(tmp_path):
    cfg_path = tmp_path / "rate_limits.json"
    cfg_path.write_text(
        (
            "{"
            '"version":"1.00",'
            '"requests_per_minute":60,'
            '"concurrent_max":2,'
            '"max_budget_tokens":5'
            "}"
        ),
        encoding="utf-8",
    )
    gatekeeper = ApiGatekeeper(cfg_path)

    assert gatekeeper.execute(lambda: "ok", projected_cost_tokens=3) == "ok"
    with pytest.raises(BudgetExceededException):
        gatekeeper.execute(lambda: "blocked", projected_cost_tokens=3)


def test_token_usage_accumulates_input_and_output_counts(tmp_path):
    cfg_path = tmp_path / "rate_limits.json"
    cfg_path.write_text(
        '{"version":"1.00","requests_per_minute":60,"concurrent_max":2}',
        encoding="utf-8",
    )
    gatekeeper = ApiGatekeeper(cfg_path)

    result = {"usage": {"input": 9, "output": 4}}
    assert gatekeeper.execute(lambda: result, input_tokens=3, output_tokens=2) == result

    usage = gatekeeper.token_usage
    assert usage["input_tokens"] == 9.0
    assert usage["output_tokens"] == 4.0


def test_version_mismatch_fails_fast_during_initialization(tmp_path):
    cfg_path = tmp_path / "rate_limits.json"
    cfg_path.write_text(
        '{"version":"9.99","requests_per_minute":60,"concurrent_max":2}',
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="version mismatch"):
        ApiGatekeeper(cfg_path)
