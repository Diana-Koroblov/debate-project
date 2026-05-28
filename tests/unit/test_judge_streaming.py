"""Tests for judge live-stream hooks used by the CLI."""

from __future__ import annotations

import multiprocessing
from unittest.mock import MagicMock, patch

from debate_sdk.services.judge_agent import ParentJudgeAgent
from debate_sdk.shared.contracts import ArgumentPayload, ChildToParentMessage


def _config(rounds: int = 3) -> dict:
    return {
        "version": "1.00",
        "stream_events": True,
        "watchdog": {"timeout_seconds": 10, "check_interval_seconds": 2},
        "debate": {"rounds": rounds, "model": "llama-3.1-8b-instant"},
    }


def test_judge_uses_configured_round_limit() -> None:
    with patch("debate_sdk.services.groq_mixin.httpx.Client"):
        judge = ParentJudgeAgent(
            "judge",
            _config(rounds=4),
            multiprocessing.Queue(),
            multiprocessing.Queue(),
        )

    assert judge.max_rounds == 4


def test_judge_forwards_argument_to_outbound_stream() -> None:
    with patch("debate_sdk.services.groq_mixin.httpx.Client"):
        outbound = multiprocessing.Queue()
        judge = ParentJudgeAgent("judge", _config(), multiprocessing.Queue(), outbound)
        judge.active_agent_id = "pro_agent"
        judge.pro_process = MagicMock(pid=100)
        judge.con_process = MagicMock(pid=200)

        judge.handle_message(
            ChildToParentMessage(
                agent_id="pro_agent",
                round_number=1,
                payload=ArgumentPayload(text="stream me"),
            )
        )

    streamed = outbound.get(timeout=1)
    assert streamed["type"] == "argument"
    assert streamed["payload"]["text"] == "stream me"
