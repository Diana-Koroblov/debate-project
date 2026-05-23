"""Unit tests for the ParentJudgeAgent orchestrator."""

from __future__ import annotations

import multiprocessing
from unittest.mock import MagicMock, patch

import pytest
from debate_sdk.shared.contracts import ChildToParentMessage, ArgumentPayload, HeartbeatMessage
from debate_sdk.services.judge_agent import ParentJudgeAgent


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
            "model": "gemini-test",
        }
    }


def test_judge_initialization(mock_config):
    """Test that the judge initializes with correct queues and Gemini mixin."""
    with patch("google.generativeai.GenerativeModel"):
        inbound = multiprocessing.Queue()
        outbound = multiprocessing.Queue()
        judge = ParentJudgeAgent("judge_1", mock_config, inbound, outbound)
        
        assert judge.agent_id == "judge_1"
        assert judge.pro_inbound is not None
        assert judge.con_inbound is not None
        assert hasattr(judge, "_model")


def test_spawn_children(mock_config):
    """Test that spawn_children creates and starts child processes."""
    with patch("google.generativeai.GenerativeModel"):
        with patch("multiprocessing.Process") as mock_process:
            # Configure mock processes to have integer PIDs to avoid PicklingError
            mock_pro = MagicMock()
            mock_pro.pid = 101
            mock_con = MagicMock()
            mock_con.pid = 102
            mock_process.side_effect = [mock_pro, mock_con]

            inbound = multiprocessing.Queue()
            outbound = multiprocessing.Queue()
            judge = ParentJudgeAgent("judge_1", mock_config, inbound, outbound)
            
            judge.spawn_children()
            
            # Should have called Process twice
            assert mock_process.call_count == 2
            mock_pro.start.assert_called_once()
            mock_con.start.assert_called_once()


def test_terminate_children(mock_config):
    """Test that terminate_children calls the termination utility."""
    with patch("google.generativeai.GenerativeModel"):
        # Patch the utility where it is USED (in the mixin module or via judge)
        with patch("debate_sdk.services.judge_process_mixin.terminate_process_tree") as mock_term:
            inbound = multiprocessing.Queue()
            outbound = multiprocessing.Queue()
            judge = ParentJudgeAgent("judge_1", mock_config, inbound, outbound)
            
            # Setup mock processes
            mock_pro = MagicMock()
            mock_pro.pid = 123
            mock_con = MagicMock()
            mock_con.pid = 456
            judge.pro_process = mock_pro
            judge.con_process = mock_con
            
            judge.terminate_children()
            
            # Should have called terminate_process_tree for both PIDs
            assert mock_term.call_count == 2
            mock_term.assert_any_call(123)
            mock_term.assert_any_call(456)


def test_judge_records_argument(mock_config):
    """Test that the judge records incoming arguments and saves state."""
    with patch("google.generativeai.GenerativeModel"):
        with patch("debate_sdk.shared.state_manager.StateManager.save_state") as mock_save:
            inbound = multiprocessing.Queue()
            outbound = multiprocessing.Queue()
            judge = ParentJudgeAgent("judge_1", mock_config, inbound, outbound)
            judge.active_agent_id = "pro_agent"
            judge.pro_process = MagicMock(pid=101)
            judge.con_process = MagicMock(pid=102)

            msg = ChildToParentMessage(
                agent_id="pro_agent",
                round_number=1,
                payload=ArgumentPayload(text="Test argument")
            )

            judge.handle_message(msg)

            # Verify ledger has the entry
            assert len(judge.ledger.entries) == 1
            assert judge.ledger.entries[0]["text"] == "Test argument"

            # Verify backup was triggered
            assert mock_save.called
            saved_state = mock_save.call_args[0][0]
            assert len(saved_state["ledger"]) == 1


def test_judge_routing_logic(mock_config):
    """Test the deterministic routing switch (Sub-task 6.3.2)."""
    with patch("google.generativeai.GenerativeModel"):
        inbound = multiprocessing.Queue()
        outbound = multiprocessing.Queue()
        judge = ParentJudgeAgent("judge_1", mock_config, inbound, outbound)
        
        # Mock child processes for heartbeat logic
        judge.pro_process = MagicMock(pid=101)
        judge.con_process = MagicMock(pid=102)
        
        # Start debate
        judge.start_debate()
        assert judge.current_round == 1
        assert judge.active_agent_id == "pro_agent"
        
        # Simulate Pro argument
        pro_msg = ChildToParentMessage(
            agent_id="pro_agent", round_number=1,
            payload=ArgumentPayload(text="Pro says hi")
        )
        judge.handle_message(pro_msg)
        
        # Next should be Con
        assert judge.active_agent_id == "con_agent"
        assert judge.current_round == 1
        
        # Simulate Con argument
        con_msg = ChildToParentMessage(
            agent_id="con_agent", round_number=1,
            payload=ArgumentPayload(text="Con rebuts")
        )
        judge.handle_message(con_msg)
        
        # Next round should start with Pro
        assert judge.active_agent_id == "pro_agent"
        assert judge.current_round == 2


def test_judge_enforces_10_rounds(mock_config):
    """Test that the debate stops after 10 rounds (Sub-task 6.3.1)."""
    with patch("google.generativeai.GenerativeModel"):
        inbound = multiprocessing.Queue()
        outbound = multiprocessing.Queue()
        judge = ParentJudgeAgent("judge_1", mock_config, inbound, outbound)
        judge.pro_process = MagicMock(pid=101)
        judge.con_process = MagicMock(pid=102)
        
        judge.current_round = 10
        judge.active_agent_id = "con_agent"
        
        con_msg = ChildToParentMessage(
            agent_id="con_agent", round_number=10,
            payload=ArgumentPayload(text="Final word")
        )
        
        with patch.object(judge.logger, "info") as mock_info:
            judge.handle_message(con_msg)
            assert judge.active_agent_id is None


def test_judge_generates_final_judgment(mock_config):
    """Test that the judge triggers evaluation and emits judgment (Sub-task 6.4)."""
    with patch("google.generativeai.GenerativeModel"):
        inbound = multiprocessing.Queue()
        outbound = multiprocessing.Queue()
        judge = ParentJudgeAgent("judge_1", mock_config, inbound, outbound)
        judge.pro_process = MagicMock(pid=101)
        judge.con_process = MagicMock(pid=102)
        
        # Setup to trigger _route_next_turn at end of round 10
        judge.current_round = 10
        judge.active_agent_id = "con_agent"
        
        mock_judgment = '{"type": "final_judgment", "winner_id": "pro_agent", "differential_score": 5.0, "justification": []}'
        
        with patch.object(judge, "generate_argument", return_value=mock_judgment):
            con_msg = ChildToParentMessage(
                agent_id="con_agent", round_number=10,
                payload=ArgumentPayload(text="End")
            )
            judge.handle_message(con_msg)
            
            # Verify judgment reached outbound
            final_msg = outbound.get(timeout=1.0)
            assert final_msg["type"] == "final_judgment"
            assert final_msg["winner_id"] == "pro_agent"
            assert final_msg["differential_score"] == 5.0


def test_judge_updates_heartbeat(mock_config):
    """Test that any message from an agent updates its heartbeat (Sub-task 6.3.4)."""
    with patch("google.generativeai.GenerativeModel"):
        inbound = multiprocessing.Queue()
        outbound = multiprocessing.Queue()
        judge = ParentJudgeAgent("judge_1", mock_config, inbound, outbound)
        judge.pro_process = MagicMock(pid=101)
        
        with patch.object(judge.watchdog, "heartbeat") as mock_hb:
            # Test with explicit HeartbeatMessage
            hb_msg = HeartbeatMessage(agent_id="pro_agent", timestamp="now")
            judge.handle_message(hb_msg)
            mock_hb.assert_called_with(101)
            
            # Test with Argument message
            mock_hb.reset_mock()
            judge.active_agent_id = "pro_agent"
            arg_msg = ChildToParentMessage(
                agent_id="pro_agent", round_number=1,
                payload=ArgumentPayload(text="Hi")
            )
            judge.handle_message(arg_msg)
            mock_hb.assert_called_with(101)
