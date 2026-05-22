"""Centralized API gatekeeper for network call entry and logging."""

from __future__ import annotations

import logging
import threading
import time
from collections import deque
from collections.abc import Callable
from pathlib import Path
from queue import Empty, Full, Queue
from typing import Any

from debate_sdk.shared.config import load_rate_limits
from debate_sdk.shared.gatekeeper_runtime import Task, run_with_retries


class ApiGatekeeper:
    """Thread-safe singleton wrapper for API call execution and telemetry logging."""

    _instance: ApiGatekeeper | None = None
    _instance_lock = threading.Lock()

    def __new__(
        cls, config_path: Path | str | None = None, *, time_fn: Callable[[], float] | None = None,
        sleeper: Callable[[float], None] | None = None
    ) -> ApiGatekeeper:
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(
        self, config_path: Path | str | None = None, *, time_fn: Callable[[], float] | None = None,
        sleeper: Callable[[float], None] | None = None
    ) -> None:
        if getattr(self, "_initialized", False):
            return
        self._logger = logging.getLogger(__name__)
        self._config = load_rate_limits(config_path)
        self._time_fn = time_fn or time.monotonic
        self._sleeper = sleeper or time.sleep
        self._requests_per_minute = self._config["requests_per_minute"]
        self._concurrency_max = self._config["concurrent_max"]
        self._queue_max_size = self._config.get("queue_max_size", 100)
        self._max_retries = self._config.get("max_retries", 3)
        self._backoff_base_seconds = self._config.get("backoff_base_seconds", 0.25)
        self._timestamps: deque[float] = deque()
        self._rate_lock = threading.Lock()
        self._concurrency_semaphore = threading.BoundedSemaphore(self._concurrency_max)
        self._queue: Queue[Task] = Queue(maxsize=self._queue_max_size)
        self._shutdown = threading.Event()
        self._dispatcher = threading.Thread(target=self._dispatch_loop, daemon=True)
        self._dispatcher.start()
        self._initialized = True

    @property
    def config(self) -> dict[str, Any]:
        return dict(self._config)

    @classmethod
    def reset_instance(cls) -> None:
        """Reset singleton state for isolated unit tests."""
        with cls._instance_lock:
            if cls._instance is not None:
                cls._instance.shutdown()
            cls._instance = None

    def shutdown(self) -> None:
        self._shutdown.set()
        self._dispatcher.join(timeout=0.5)

    def _prune_timestamps(self, now: float) -> None:
        while self._timestamps and now - self._timestamps[0] >= 60.0:
            self._timestamps.popleft()

    def _retry_after_seconds(self) -> float:
        with self._rate_lock:
            now = self._time_fn()
            self._prune_timestamps(now)
            if len(self._timestamps) < self._requests_per_minute:
                return 0.0
            return max(0.0, 60.0 - (now - self._timestamps[0]))

    def _try_acquire_slot(self) -> tuple[bool, float]:
        if not self._concurrency_semaphore.acquire(blocking=False):
            return False, max(0.01, self._retry_after_seconds())
        with self._rate_lock:
            now = self._time_fn()
            self._prune_timestamps(now)
            if len(self._timestamps) < self._requests_per_minute:
                self._timestamps.append(now)
                return True, 0.0
        self._concurrency_semaphore.release()
        return False, max(0.01, self._retry_after_seconds())

    def _run_task(self, task: Task) -> None:
        call_name = getattr(task.api_call, "__name__", repr(task.api_call))
        try:
            task.result = run_with_retries(
                task.api_call,
                self._logger,
                self._sleeper,
                self._max_retries,
                self._backoff_base_seconds,
                *task.args,
                **task.kwargs,
            )
            self._logger.info("api_call_success name=%s", call_name)
        except Exception as exc:
            task.error = exc
            self._logger.exception("api_call_failure name=%s", call_name)
        finally:
            self._logger.info("api_call_complete name=%s", call_name)
            task.done.set()

    def _dispatch_loop(self) -> None:
        while not self._shutdown.is_set():
            try:
                task = self._queue.get(timeout=0.1)
            except Empty:
                continue
            acquired = False
            while not self._shutdown.is_set():
                acquired, wait_seconds = self._try_acquire_slot()
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
                    self._concurrency_semaphore.release()
            self._queue.task_done()

    def execute(self, api_call: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Execute an API call through the gatekeeper and log all traffic attempts."""
        call_name = getattr(api_call, "__name__", repr(api_call))
        self._logger.info("api_call_start name=%s", call_name)
        task = Task(api_call=api_call, args=args, kwargs=kwargs, done=threading.Event())

        acquired, retry_after_seconds = self._try_acquire_slot()
        if acquired:
            try:
                self._run_task(task)
            finally:
                self._concurrency_semaphore.release()
        else:
            try:
                self._queue.put_nowait(task)
                self._logger.info(
                    "api_call_queued name=%s retry_after_seconds=%.3f",
                    call_name,
                    retry_after_seconds,
                )
            except Full as exc:
                raise RuntimeError("API gatekeeper overflow queue is full") from exc

        task.done.wait()
        if task.error:
            raise task.error
        return task.result
