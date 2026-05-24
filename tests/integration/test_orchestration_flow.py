"""Integration tests for the full debate orchestration flow."""

from __future__ import annotations

import multiprocessing
import queue
import time
from typing import Any, Dict

import pytest

from debate_sdk.services.child_agent import ChildDebaterAgent
from debate_sdk.services.judge_agent import ParentJudgeAgent
from debate_sdk.shared.contracts import FinalJudgmentSchema, JudgmentJustification
from debate_sdk.shared.exceptions import BudgetExceededException


class MockDebater(ChildDebaterAgent):
    """6.6.2: Mock child fixture that responds instantly with valid JSON."""

    def generate_argument(self, prompt: str) -> str:
        """Simulate LLM response without network calls."""
        return '{"text": "Mock argument", "citations": []}'


class MockJudge(ParentJudgeAgent):
    """Mock judge that avoids Gemini calls for integration tests."""

    def evaluate_debate(self, history: list[str]) -> FinalJudgmentSchema:
        return FinalJudgmentSchema(
            winner_id='pro_agent',
            differential_score=5.0,
            justification=[JudgmentJustification(point="MOCK_POINT", evidence="mock")]
        )


class MockBudgetJudge(MockJudge):
    """Mock judge that hits budget cap midway."""

    def handle_message(self, message: Any) -> None:
        # Raise budget exception on the first argument received to test resilience
        from debate_sdk.shared.contracts import ChildToParentMessage
        if isinstance(message, ChildToParentMessage):
             raise BudgetExceededException("Integration test judge budget hit")
        super().handle_message(message)


@pytest.fixture
def integration_config():
    """Valid system configuration for integration testing."""
    return {
        "version": "1.00",
        "watchdog": {"timeout_seconds": 30, "check_interval_seconds": 5},
        "debate": {"rounds": 2, "model": "mock-model"}
    }


def _run_judge(judge_cls: type[ParentJudgeAgent], config: Dict[str, Any],
               inbound: multiprocessing.Queue, outbound: multiprocessing.Queue,
               pro_cls: type[ChildDebaterAgent], con_cls: type[ChildDebaterAgent]):
    """Worker to start debate and run judge event loop."""
    import os
    os.environ["GOOGLE_API_KEY"] = "mock-key"

    judge = judge_cls("judge_worker", config, inbound, outbound)
    judge.spawn_children(pro_cls=pro_cls, con_cls=con_cls)
    judge.start_debate()
    judge.run()
    judge.terminate_children()


def test_full_debate_orchestration(integration_config):
    """6.6.3: Verify orchestrator executes rounds and terminates smoothly."""
    inbound, outbound = multiprocessing.Queue(), multiprocessing.Queue()

    try:
        judge_proc = multiprocessing.Process(
            target=_run_judge,
            args=(MockJudge, integration_config, inbound, outbound, MockDebater, MockDebater)
        )
        judge_proc.start()

        final_msg = None
        start_time = time.time()
        while time.time() - start_time < 15:
            try:
                msg = outbound.get(timeout=0.5)
                if isinstance(msg, dict) and msg.get("type") == "final_judgment":
                    final_msg = msg
                    break
            except (queue.Empty, EOFError, BrokenPipeError):
                continue

        assert final_msg is not None
        assert final_msg["winner_id"] == "pro_agent"

    finally:
        if 'judge_proc' in locals() and judge_proc.is_alive():
            judge_proc.terminate()
            judge_proc.join()


def test_budget_exhaustion_mid_debate(integration_config):
    """6.6.4: Mock budget exhaustion midway and verify graceful degradation."""
    inbound, outbound = multiprocessing.Queue(), multiprocessing.Queue()

    try:
        # Use MockBudgetJudge which raises BudgetExceededException
        judge_proc = multiprocessing.Process(
            target=_run_judge,
            args=(MockBudgetJudge, integration_config, inbound, outbound, MockDebater, MockDebater)
        )
        judge_proc.start()

        final_msg = None
        start_time = time.time()
        while time.time() - start_time < 15:
            try:
                msg = outbound.get(timeout=0.5)
                if isinstance(msg, dict) and msg.get("type") == "final_judgment":
                    final_msg = msg
                    break
            except (queue.Empty, EOFError, BrokenPipeError):
                continue

        assert final_msg is not None
        assert any(j["point"] == "RESOURCE_TRUNCATION" for j in final_msg["justification"])

    finally:
        if 'judge_proc' in locals() and judge_proc.is_alive():
            judge_proc.terminate()
            judge_proc.join()
