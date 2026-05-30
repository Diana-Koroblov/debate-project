"""Rate-limit and queue orchestration for the API gatekeeper."""

from __future__ import annotations

import threading
from collections import deque
from collections.abc import Callable
from queue import Empty, Queue

from debate_sdk.shared.gatekeeper_runtime import Task


class TrafficController:
    def __init__(
        self,
        requests_per_minute: int,
        tokens_per_minute: float,
        concurrency_max: int,
        queue_max_size: int,
        time_fn: Callable[[], float],
        sleeper: Callable[[float], None],
        run_task: Callable[[Task], None],
    ) -> None:
        self._requests_per_minute = requests_per_minute
        self._tokens_per_minute = float(tokens_per_minute)
        self._time_fn = time_fn
        self._sleeper = sleeper
        self._run_task = run_task
        self._timestamps: deque[float] = deque()
        self._token_timestamps: deque[tuple[float, float]] = deque()
        self._rate_lock = threading.Lock()
        self._semaphore = threading.BoundedSemaphore(concurrency_max)
        self._queue: Queue[Task] = Queue(maxsize=queue_max_size)
        self._shutdown = threading.Event()
        self._dispatcher = threading.Thread(target=self._dispatch_loop, daemon=True)
        self._dispatcher.start()

    @property
    def queue(self) -> Queue[Task]:
        return self._queue

    def shutdown(self) -> None:
        self._shutdown.set()
        self._dispatcher.join(timeout=0.5)

    def _prune_timestamps(self, now: float) -> None:
        while self._timestamps and now - self._timestamps[0] >= 60.0:
            self._timestamps.popleft()

    def _prune_token_timestamps(self, now: float) -> None:
        while self._token_timestamps and now - self._token_timestamps[0][0] >= 60.0:
            self._token_timestamps.popleft()

    def _token_usage(self) -> float:
        return sum(tokens for _, tokens in self._token_timestamps)

    def retry_after_seconds(self, projected_cost: float = 0.0) -> float:
        with self._rate_lock:
            now = self._time_fn()
            self._prune_timestamps(now)
            self._prune_token_timestamps(now)
            waits: list[float] = []
            if len(self._timestamps) >= self._requests_per_minute:
                waits.append(max(0.0, 60.0 - (now - self._timestamps[0])))
            if self._tokens_per_minute > 0:
                token_usage = self._token_usage()
                if token_usage + projected_cost > self._tokens_per_minute:
                    tokens_to_free = token_usage + projected_cost - self._tokens_per_minute
                    released = 0.0
                    for timestamp, tokens in self._token_timestamps:
                        waits.append(max(0.0, 60.0 - (now - timestamp)))
                        released += tokens
                        if released >= tokens_to_free:
                            break
            if not waits:
                return 0.0
            return max(waits)

    def try_acquire_slot(self, projected_cost: float = 0.0) -> tuple[bool, float]:
        if not self._semaphore.acquire(blocking=False):
            return False, max(0.01, self.retry_after_seconds(projected_cost))
        with self._rate_lock:
            now = self._time_fn()
            self._prune_timestamps(now)
            self._prune_token_timestamps(now)
            token_usage = self._token_usage()
            tokens_allowed = (
                self._tokens_per_minute <= 0
                or token_usage + projected_cost <= self._tokens_per_minute
            )
            if (
                len(self._timestamps) < self._requests_per_minute
                and tokens_allowed
            ):
                self._timestamps.append(now)
                if projected_cost > 0 and self._tokens_per_minute > 0:
                    self._token_timestamps.append((now, projected_cost))
                return True, 0.0
        self._semaphore.release()
        return False, max(0.01, self.retry_after_seconds(projected_cost))

    def release_slot(self) -> None:
        self._semaphore.release()

    def _dispatch_loop(self) -> None:
        while not self._shutdown.is_set():
            try:
                task = self._queue.get(timeout=0.1)
            except Empty:
                continue
            acquired = False
            while not self._shutdown.is_set():
                acquired, wait_seconds = self.try_acquire_slot(task.projected_cost)
                if acquired:
                    break
                self._sleeper(wait_seconds)
            if not acquired:
                task.error = RuntimeError("Gatekeeper shut down before queued task could run")
                task.done.set()
            else:
                try:
                    self._run_task(task)
                finally:
                    self.release_slot()
            self._queue.task_done()

    def enqueue(self, task: Task) -> None:
        self._queue.put_nowait(task)
