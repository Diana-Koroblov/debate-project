"""Tests for token-usage parsing and cost summaries."""

from pathlib import Path

from debate_sdk.sdk.pricing import build_cost_summary, write_cost_summary


def test_build_cost_summary_and_write_artifact(tmp_path: Path) -> None:
    usage = {
        "input_tokens": 1000000.0,
        "output_tokens": 200000.0,
        "tracked_consumption": 3000.0
    }

    summary = build_cost_summary("gemini-1.5-pro", usage)
    artifact = write_cost_summary(summary, tmp_path, "session-1")

    assert summary["costs"]["input_cost_usd"] == 1.25
    assert summary["costs"]["output_cost_usd"] == 1.0
    assert artifact.name == "cost_summary_session-1.json"
    assert artifact.exists()
