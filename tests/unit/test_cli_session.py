"""Tests for the SDK debate session runner."""

from __future__ import annotations

import multiprocessing
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from debate_sdk.sdk.session import DebateSessionOptions, build_session_config, run_debate_session
from debate_sdk.sdk.transcript import write_transcript


class StubJudge:
    """Minimal judge stub for exercising the session worker."""

    def __init__(self, agent_id: str, config: dict, inbound, outbound) -> None:
        self.outbound = outbound
        self.config = config

    def spawn_children(self, pro_cls=None, con_cls=None) -> None:
        return None

    def start_debate(self) -> None:
        return None

    def run(self) -> None:
        self.outbound.put(
            {
                "type": "argument",
                "agent_id": "pro_agent",
                "round_number": 1,
                "payload": {"text": "stub argument", "citations": [], "search_queries": []},
            }
        )
        self.outbound.put(
            {
                "type": "final_judgment",
                "winner_id": "pro_agent",
                "differential_score": 2.0,
                "justification": [],
            }
        )

    def terminate_children(self) -> None:
        return None


def test_build_session_config_clamps_rounds(monkeypatch) -> None:
    monkeypatch.setattr(
        "debate_sdk.sdk.session.load_setup_config",
        lambda config_path=None: {
            "version": "1.00",
            "watchdog": {},
            "debate": {"rounds": 4, "model": "gemini-2.5-flash"},
        },
    )

    config = build_session_config(DebateSessionOptions(rounds=10, session_id="abc"))

    assert config["debate"]["rounds"] == 4
    assert config["session_id"] == "abc"
    assert config["stream_events"] is True


def test_run_debate_session_streams_events(monkeypatch, tmp_path: Path) -> None:
    multiprocessing.set_start_method("spawn", force=True)
    monkeypatch.setattr(
        "debate_sdk.sdk.session.load_setup_config",
        lambda config_path=None: {
            "version": "1.00",
            "watchdog": {"timeout_seconds": 1, "check_interval_seconds": 1},
            "debate": {"rounds": 3, "model": "gemini-2.5-flash"},
        },
    )
    monkeypatch.setattr(
        "debate_sdk.sdk.session.write_cost_summary",
        lambda summary, results_dir, session_id: tmp_path / f"{session_id}.json",
    )
    monkeypatch.setattr(
        "debate_sdk.sdk.session.write_transcript",
        lambda transcript, results_dir, session_id: write_transcript(transcript, tmp_path, session_id),
    )

    events: list[str] = []
    result = run_debate_session(
        DebateSessionOptions(rounds=2, session_id="session-test"),
        on_event=lambda event: events.append(event["type"]),
        judge_cls=StubJudge,
    )

    assert events == ["argument", "final_judgment"]
    assert result.final_judgment["winner_id"] == "pro_agent"
    assert result.artifact_path == tmp_path / "session-test.json"
    assert result.transcript_path == tmp_path / "transcript_session-test.md"
    assert result.transcript_path.read_text(encoding="utf-8").startswith(
        "# Debate Transcript session-test"
    )


def test_run_debate_session_worker_is_not_daemon(monkeypatch) -> None:
    fake_worker = MagicMock()
    fake_worker.is_alive.return_value = False
    process_cls = MagicMock(return_value=fake_worker)

    monkeypatch.setattr(
        "debate_sdk.sdk.session.load_setup_config",
        lambda config_path=None: {
            "version": "1.00",
            "watchdog": {"timeout_seconds": 1, "check_interval_seconds": 1},
            "debate": {"rounds": 1, "model": "gemini-2.5-flash"},
        },
    )
    monkeypatch.setattr("debate_sdk.sdk.session.multiprocessing.Process", process_cls)

    with pytest.raises(RuntimeError, match="final judgment"):
        run_debate_session(DebateSessionOptions(rounds=1, session_id="daemon-check"))

    assert process_cls.call_args.kwargs.get("daemon", False) is False
