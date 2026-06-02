"""Tests for the gatekeeper traffic controller."""

from __future__ import annotations

import threading

from debate_sdk.shared.gatekeeper_runtime import Task
from debate_sdk.shared.gatekeeper_traffic import TrafficController


class FakeClock:
    def __init__(self, value: float = 0.0) -> None:
        self.value = value

    def now(self) -> float:
        return self.value

    def sleep(self, seconds: float) -> None:
        self.value += seconds


def test_retry_after_seconds_prunes_old_entries_and_uses_longest_wait() -> None:
    clock = FakeClock(120.0)
    controller = TrafficController(
        requests_per_minute=1,
        tokens_per_minute=6,
        concurrency_max=2,
        queue_max_size=2,
        time_fn=clock.now,
        sleeper=clock.sleep,
        run_task=lambda task: None,
    )

    try:
        controller._timestamps.extend([30.0, 70.0])
        controller._token_timestamps.extend([(10.0, 2.0), (80.0, 4.0)])

        assert controller.retry_after_seconds(projected_cost=4.0) == 20.0
        assert list(controller._timestamps) == [70.0]
        assert list(controller._token_timestamps) == [(80.0, 4.0)]
    finally:
        controller.shutdown()


def test_try_acquire_slot_handles_concurrency_and_token_limits() -> None:
    clock = FakeClock()
    controller = TrafficController(
        requests_per_minute=2,
        tokens_per_minute=5,
        concurrency_max=1,
        queue_max_size=2,
        time_fn=clock.now,
        sleeper=clock.sleep,
        run_task=lambda task: None,
    )

    try:
        acquired, wait_seconds = controller.try_acquire_slot(projected_cost=4.0)
        assert acquired is True
        assert wait_seconds == 0.0

        blocked, blocked_wait = controller.try_acquire_slot(projected_cost=1.0)
        assert blocked is False
        assert blocked_wait >= 0.01

        controller.release_slot()

        denied, denied_wait = controller.try_acquire_slot(projected_cost=2.0)
        assert denied is False
        assert denied_wait >= 59.0

        retry_acquired, retry_wait = controller.try_acquire_slot(projected_cost=0.0)
        assert retry_acquired is True
        assert retry_wait == 0.0
        controller.release_slot()
    finally:
        controller.shutdown()


def test_dispatch_loop_runs_enqueued_task_and_releases_slot() -> None:
    clock = FakeClock()
    ran: list[str] = []

    def run_task(task: Task) -> None:
        task.result = "done"
        ran.append(task.result)
        task.done.set()

    controller = TrafficController(
        requests_per_minute=10,
        tokens_per_minute=0,
        concurrency_max=1,
        queue_max_size=2,
        time_fn=clock.now,
        sleeper=clock.sleep,
        run_task=run_task,
    )

    try:
        task = Task(api_call=lambda: None, args=(), kwargs={}, done=threading.Event())
        assert controller.queue.qsize() == 0

        controller.enqueue(task)

        assert task.done.wait(timeout=1.0)
        assert ran == ["done"]
        assert task.error is None

        acquired, _ = controller.try_acquire_slot()
        assert acquired is True
        controller.release_slot()
    finally:
        controller.shutdown()


def test_dispatch_loop_fails_pending_task_when_shutdown_happens_mid_wait() -> None:
    clock = FakeClock()
    controller_ref: dict[str, TrafficController] = {}

    def sleeper(seconds: float) -> None:
        clock.sleep(seconds)
        controller_ref["controller"]._shutdown.set()

    controller = TrafficController(
        requests_per_minute=10,
        tokens_per_minute=0,
        concurrency_max=1,
        queue_max_size=2,
        time_fn=clock.now,
        sleeper=sleeper,
        run_task=lambda task: task.done.set(),
    )
    controller_ref["controller"] = controller

    acquired, _ = controller.try_acquire_slot()
    assert acquired is True

    try:
        task = Task(api_call=lambda: None, args=(), kwargs={}, done=threading.Event())
        controller.enqueue(task)

        assert task.done.wait(timeout=1.0)
        assert isinstance(task.error, RuntimeError)
        assert "Gatekeeper shut down" in str(task.error)
    finally:
        controller.release_slot()
        controller.shutdown()