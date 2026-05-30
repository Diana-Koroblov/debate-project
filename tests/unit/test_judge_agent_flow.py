"""Flow-oriented unit tests for ParentJudgeAgent routing and outcomes."""

from __future__ import annotations

import multiprocessing
from unittest.mock import MagicMock, patch

import pytest

from debate_sdk.services.judge_agent import ParentJudgeAgent
from debate_sdk.shared.contracts import ArgumentPayload, ChildToParentMessage, HeartbeatMessage


@pytest.fixture
def mock_config() -> dict:
    return {
        "version": "1.00",
        "watchdog": {"timeout_seconds": 10, "check_interval_seconds": 2},
        "debate": {"model": "llama-3.1-8b-instant"},
    }


def test_judge_routing_logic(mock_config: dict) -> None:
    """Verify deterministic turn routing between Pro and Con."""
    with (
        patch("debate_sdk.services.groq_mixin.httpx.Client"),
        patch.object(ParentJudgeAgent, "_decide_topic", return_value="Generated topic"),
    ):
        judge = ParentJudgeAgent(
            "judge_1",
            mock_config,
            multiprocessing.Queue(),
            multiprocessing.Queue(),
        )
        judge.pro_process = MagicMock(pid=101)
        judge.con_process = MagicMock(pid=102)

        judge.start_debate()
        assert judge.current_round == 1
        assert judge.active_agent_id == "pro_agent"

        judge.handle_message(
            ChildToParentMessage(
                agent_id="pro_agent",
                round_number=1,
                payload=ArgumentPayload(text="Pro says hi"),
            )
        )
        assert judge.active_agent_id == "con_agent"

        judge.handle_message(
            ChildToParentMessage(
                agent_id="con_agent",
                round_number=1,
                payload=ArgumentPayload(text="Con rebuts"),
            )
        )
        assert judge.active_agent_id == "pro_agent"
        assert judge.current_round == 2


def test_judge_enforces_round_limit(mock_config: dict) -> None:
    """Verify the judge ends debate when configured round limit is reached."""
    with (
        patch("debate_sdk.services.groq_mixin.httpx.Client"),
        patch.object(ParentJudgeAgent, "_decide_topic", return_value="Generated topic"),
    ):
        judge = ParentJudgeAgent(
            "judge_1",
            mock_config,
            multiprocessing.Queue(),
            multiprocessing.Queue(),
        )
        judge.pro_process = MagicMock(pid=101)
        judge.con_process = MagicMock(pid=102)
        judge.current_round = 10
        judge.active_agent_id = "con_agent"

        judge.handle_message(
            ChildToParentMessage(
                agent_id="con_agent",
                round_number=10,
                payload=ArgumentPayload(text="Final word"),
            )
        )

        assert judge.active_agent_id is None


def test_judge_generates_final_judgment(mock_config: dict) -> None:
    """Verify final judgment is emitted onto outbound queue."""
    with (
        patch("debate_sdk.services.groq_mixin.httpx.Client"),
        patch.object(ParentJudgeAgent, "_decide_topic", return_value="Generated topic"),
    ):
        inbound = multiprocessing.Queue()
        outbound = multiprocessing.Queue()
        judge = ParentJudgeAgent("judge_1", mock_config, inbound, outbound)
        judge.pro_process = MagicMock(pid=101)
        judge.con_process = MagicMock(pid=102)
        judge.current_round = 10
        judge.active_agent_id = "con_agent"

        mock_judgment = (
            '{"type":"final_judgment","winner_id":"pro_agent",'
            '"differential_score":5.0,"justification":[]}'
        )
        with patch.object(judge, "generate_argument", return_value=mock_judgment):
            judge.handle_message(
                ChildToParentMessage(
                    agent_id="con_agent",
                    round_number=10,
                    payload=ArgumentPayload(text="End"),
                )
            )

        final_msg = outbound.get(timeout=1.0)
        assert final_msg["type"] == "final_judgment"
        assert final_msg["winner_id"] == "pro_agent"


def test_judge_normalizes_string_justification_and_winner_key(mock_config: dict) -> None:
    """Verify the judge coerces common model schema mistakes into the contract."""
    with (
        patch("debate_sdk.services.groq_mixin.httpx.Client"),
        patch.object(ParentJudgeAgent, "_decide_topic", return_value="Generated topic"),
    ):
        inbound = multiprocessing.Queue()
        outbound = multiprocessing.Queue()
        judge = ParentJudgeAgent("judge_1", mock_config, inbound, outbound)
        judge.pro_process = MagicMock(pid=101)
        judge.con_process = MagicMock(pid=102)
        judge.current_round = 10
        judge.active_agent_id = "con_agent"

        malformed_judgment = (
            '{"type":"final_judgment","winner":"con_agent",'
            '"differential_score":0,"justification":"Accuracy: The con side stayed closer to current evidence."}'
        )
        with patch.object(judge, "generate_argument", return_value=malformed_judgment):
            judge.handle_message(
                ChildToParentMessage(
                    agent_id="con_agent",
                    round_number=10,
                    payload=ArgumentPayload(text="End"),
                )
            )

        final_msg = outbound.get(timeout=1.0)
        assert final_msg["winner_id"] == "con_agent"
        assert final_msg["differential_score"] == 0.1
        assert final_msg["justification"][0]["point"] == "Accuracy"


def test_judge_updates_heartbeat(mock_config: dict) -> None:
    """Verify heartbeat updates from explicit and argument messages."""
    with (
        patch("debate_sdk.services.groq_mixin.httpx.Client"),
        patch.object(ParentJudgeAgent, "_decide_topic", return_value="Generated topic"),
    ):
        judge = ParentJudgeAgent(
            "judge_1",
            mock_config,
            multiprocessing.Queue(),
            multiprocessing.Queue(),
        )
        judge.pro_process = MagicMock(pid=101)

        with patch.object(judge.watchdog, "heartbeat") as mock_hb:
            judge.handle_message(HeartbeatMessage(agent_id="pro_agent", timestamp="now"))
            mock_hb.assert_called_with(101)
            mock_hb.reset_mock()

            judge.active_agent_id = "pro_agent"
            judge.handle_message(
                ChildToParentMessage(
                    agent_id="pro_agent",
                    round_number=1,
                    payload=ArgumentPayload(text="Hi"),
                )
            )
            mock_hb.assert_called_with(101)


def test_judge_retries_malformed_output_and_accepts_con_winner(mock_config: dict) -> None:
    """Malformed judge output should be retried instead of defaulting to pro."""
    with (
        patch("debate_sdk.services.groq_mixin.httpx.Client"),
        patch.object(ParentJudgeAgent, "_decide_topic", return_value="Generated topic"),
    ):
        judge = ParentJudgeAgent(
            "judge_1",
            mock_config,
            multiprocessing.Queue(),
            multiprocessing.Queue(),
        )

        with patch.object(
            judge,
            "generate_argument",
            side_effect=[
                "not-json",
                '{"winner_id":"con_agent","differential_score":2.0,"justification":[]}',
            ],
        ):
            judgment = judge.evaluate_debate(["[pro_agent] Round 1", "[con_agent] Round 1"])

        assert judgment.winner_id == "con_agent"
        assert judgment.differential_score == 2.0


def test_judge_invalid_output_uses_neutral_fallback_not_hardcoded_pro(mock_config: dict) -> None:
    """Repeated invalid judge output should use neutral fallback winner selection."""
    with (
        patch("debate_sdk.services.groq_mixin.httpx.Client"),
        patch.object(ParentJudgeAgent, "_decide_topic", return_value="Generated topic"),
    ):
        judge = ParentJudgeAgent(
            "judge_1",
            mock_config,
            multiprocessing.Queue(),
            multiprocessing.Queue(),
        )

        with (
            patch.object(judge, "generate_argument", return_value="not-json"),
            patch.object(judge, "_neutral_fallback_winner", return_value="con_agent") as mock_fallback,
        ):
            judgment = judge.evaluate_debate(["[pro_agent] Round 1", "[con_agent] Round 1"])

        mock_fallback.assert_called_once()
        assert judgment.winner_id == "con_agent"
        assert judgment.justification[0].point == "System Recovery"
