"""Tests for token-usage parsing and cost summaries."""

from pathlib import Path

from debate_sdk.sdk.pricing import build_cost_summary, parse_token_usage, write_cost_summary


def test_parse_token_usage_reads_latest_cumulative_values(tmp_path: Path) -> None:
    log_file = tmp_path / "agent_logs_01.log"
    log_file.write_text(
        "ignore me\n"
        "token_usage_update input_tokens=100 output_tokens=25 tracked_consumption=3000.0\n"
        "token_usage_update input_tokens=150 output_tokens=40 tracked_consumption=5000.0\n",
        encoding="utf-8",
    )

    usage = parse_token_usage(tmp_path)

    assert usage == {
        "input_tokens": 150.0,
        "output_tokens": 40.0,
        "tracked_consumption": 5000.0,
    }


def test_build_cost_summary_and_write_artifact(tmp_path: Path) -> None:
    (tmp_path / "agent_logs_01.log").write_text(
        "token_usage_update input_tokens=1000000 output_tokens=200000 tracked_consumption=3000.0\n",
        encoding="utf-8",
    )

    summary = build_cost_summary("gemini-1.5-pro", tmp_path)
    artifact = write_cost_summary(summary, tmp_path, "session-1")

    assert summary["costs"]["input_cost_usd"] == 1.25
    assert summary["costs"]["output_cost_usd"] == 1.0
    assert artifact.name == "cost_summary_session-1.json"
    assert artifact.exists()
