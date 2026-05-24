"""Unit tests for ParentJudgeAgent budget exhaustion handling."""

from __future__ import annotations

import multiprocessing
from unittest.mock import MagicMock, patch

import pytest

from debate_sdk.services.judge_agent import ParentJudgeAgent
from debate_sdk.shared.contracts import (
    FinalJudgmentSchema,
)
from debate_sdk.shared.exceptions import BudgetExceededException


@pytest.fixture
def mock_config():
    """Mock configuration with watchdog settings."""
    return {
        "version": "1.00",
        "watchdog": {
            "timeout_seconds": 10,
            "check_interval_seconds": 2
        },
        "debate": {
            "model": "gemini-test",
        }
    }


def test_judge_handles_budget_exception(mock_config):
    """Test that the judge catches BudgetExceededException and degrades gracefully."""
    with patch("google.generativeai.GenerativeModel"):
        inbound = multiprocessing.Queue()
        outbound = multiprocessing.Queue()
        judge = ParentJudgeAgent("judge_1", mock_config, inbound, outbound)

        # Mock child processes with real PIDs
        judge.pro_process = MagicMock(pid=101)
        judge.con_process = MagicMock(pid=102)

        # 1. Simulate the exception being raised during handle_message
        with (
            patch.object(
                judge,
                "handle_message",
                side_effect=BudgetExceededException("Out of money"),
            ),
            patch.object(judge, "terminate_children") as mock_halt,
            patch.object(judge, "evaluate_debate") as mock_eval,
        ):
            # Setup real evaluation result
            mock_eval.return_value = FinalJudgmentSchema(
                winner_id="pro_agent",
                differential_score=1.0,
                justification=[],
            )

            # Prime the inbound queue with a real dict (serializable)
            inbound.put(
                {
                    "type": "argument",
                    "agent_id": "pro_agent",
                    "round_number": 1,
                    "payload": {"text": "hi", "search_queries": [], "citations": []},
                }
            )

            # run() will catch BudgetExceededException and call _handle_budget_failure
            judge.run()

            # Verify children were halted
            mock_halt.assert_called_once()

            # Drain queue to find final_judgment (skip heartbeats)
            final_judgment = None
            for _ in range(10):
                try:
                    msg = outbound.get(timeout=0.1)
                    if msg["type"] == "final_judgment":
                        final_judgment = msg
                        break
                except Exception:
                    break

            assert final_judgment is not None
            assert any(
                item["point"] == "RESOURCE_TRUNCATION"
                for item in final_judgment["justification"]
            )
