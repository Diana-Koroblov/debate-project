"""Unit tests for the ParentJudgeAgent orchestrator."""

from __future__ import annotations

import multiprocessing
from unittest.mock import MagicMock, patch

import pytest

from debate_sdk.services.judge_agent import ParentJudgeAgent
from debate_sdk.shared.contracts import ArgumentPayload, ChildToParentMessage


@pytest.fixture
def mock_config():
    """Mock configuration for the judge."""
    return {
        "version": "1.00",
        "watchdog": {
            "timeout_seconds": 10,
            "check_interval_seconds": 2
        },
        "debate": {
            "model": "llama-3.1-8b-instant",
        }
    }


def test_judge_initialization(mock_config):
    """Test that the judge initializes with correct queues and Groq mixin."""
    with patch("debate_sdk.services.groq_mixin.httpx.Client"):
        inbound = multiprocessing.Queue()
        outbound = multiprocessing.Queue()
        judge = ParentJudgeAgent("judge_1", mock_config, inbound, outbound)

        assert judge.agent_id == "judge_1"
        assert judge.pro_inbound is not None
        assert judge.con_inbound is not None
        assert hasattr(judge, "_model")


def test_spawn_children(mock_config):
    """Test that spawn_children creates and starts child processes."""
    with (
        patch("debate_sdk.services.groq_mixin.httpx.Client"),
        patch("multiprocessing.Process") as mock_process,
    ):
        mock_pro = MagicMock(pid=101)
        mock_con = MagicMock(pid=102)
        mock_process.side_effect = [mock_pro, mock_con]

        inbound = multiprocessing.Queue()
        outbound = multiprocessing.Queue()
        judge = ParentJudgeAgent("judge_1", mock_config, inbound, outbound)

        judge.spawn_children()

        assert mock_process.call_count == 2
        mock_pro.start.assert_called_once()
        mock_con.start.assert_called_once()


def test_terminate_children(mock_config):
    """Test that terminate_children calls the termination utility."""
    with (
        patch("debate_sdk.services.groq_mixin.httpx.Client"),
        patch("debate_sdk.services.judge_process_mixin.terminate_process_tree") as mock_term,
    ):
        inbound = multiprocessing.Queue()
        outbound = multiprocessing.Queue()
        judge = ParentJudgeAgent("judge_1", mock_config, inbound, outbound)

        judge.pro_process = MagicMock(pid=123)
        judge.con_process = MagicMock(pid=456)

        judge.terminate_children()

        assert mock_term.call_count == 2
        mock_term.assert_any_call(123)
        mock_term.assert_any_call(456)


def test_judge_records_argument(mock_config):
    """Test that the judge records incoming arguments and saves state."""
    with (
        patch("debate_sdk.services.groq_mixin.httpx.Client"),
        patch("debate_sdk.shared.state_manager.StateManager.save_state") as mock_save,
    ):
        inbound = multiprocessing.Queue()
        outbound = multiprocessing.Queue()
        judge = ParentJudgeAgent("judge_1", mock_config, inbound, outbound)
        judge.active_agent_id = "pro_agent"
        judge.pro_process = MagicMock(pid=101)
        judge.con_process = MagicMock(pid=102)

        msg = ChildToParentMessage(
            agent_id="pro_agent",
            round_number=1,
            payload=ArgumentPayload(text="Test argument"),
        )

        judge.handle_message(msg)

        assert len(judge.ledger.entries) == 1
        assert judge.ledger.entries[0]["text"] == "Test argument"
        assert mock_save.called
        saved_state = mock_save.call_args[0][0]
        assert len(saved_state["ledger"]) == 1
