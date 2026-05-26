from __future__ import annotations

import multiprocessing
import threading
import time
from collections.abc import Callable
from pathlib import Path
from queue import Full
from typing import Any

from debate_sdk.shared.config import load_rate_limits
from debate_sdk.shared.gatekeeper_budget import record_usage, reserve_budget, token_usage_snapshot
from debate_sdk.shared.gatekeeper_runtime import (
    Task,
    ensure_version_compatibility,
    run_with_retries,
)
from debate_sdk.shared.gatekeeper_traffic import TrafficController
from debate_sdk.shared.logger import setup_logger
from debate_sdk.shared.version import __version__


class ApiGatekeeper:
    _instance: ApiGatekeeper | None = None
    _instance_lock = threading.Lock()

    def __new__(
        cls, config_path: Path | str | None = None,
        *, time_fn: Callable[[], float] | None = None,
        sleeper: Callable[[float], None] | None = None,
        agent_id: str | None = None,
        model_name: str | None = None,
        outbound_queue: multiprocessing.Queue | None = None,
    ) -> ApiGatekeeper:
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(
        self, config_path: Path | str | None = None,
        *, time_fn: Callable[[], float] | None = None,
        sleeper: Callable[[float], None] | None = None,
        agent_id: str | None = None,
        model_name: str | None = None,
        outbound_queue: multiprocessing.Queue | None = None,
    ) -> None:
        if getattr(self, "_initialized", False):
            return
        self._logger = setup_logger("gatekeeper")
        self._agent_id = agent_id
        self._model_name = model_name
        self._outbound_queue = outbound_queue
        self._config = load_rate_limits(config_path)
        self._sleeper = sleeper or time.sleep
        self._max_retries = self._config.get("max_retries", 3)
        self._backoff_base_seconds = self._config.get("backoff_base_seconds", 0.25)
        self._max_budget_tokens = self._config.get("max_budget_tokens", 100000.0)
        self._budget_lock = threading.Lock()
        self._input_tokens_total = 0
        self._output_tokens_total = 0
        self._tracked_token_consumption = 0.0
        self._traffic = TrafficController(
            requests_per_minute=self._config["requests_per_minute"],
            concurrency_max=self._config["concurrent_max"],
            queue_max_size=self._config.get("queue_max_size", 100),
            time_fn=time_fn or time.monotonic,
            sleeper=self._sleeper,
            run_task=self._run_task,
        )
        ensure_version_compatibility(self._config["version"], __version__, self._logger)
        self._initialized = True

    @classmethod
    def reset_instance(cls) -> None:
        with cls._instance_lock:
            if cls._instance is not None:
                cls._instance._traffic.shutdown()
            cls._instance = None

    @property
    def token_usage(self) -> dict[str, float]:
        return token_usage_snapshot(self)

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
            record_usage(self, task)
            if self._outbound_queue is not None:
                try:
                    self._outbound_queue.put_nowait({
                        "type": "telemetry",
                        "agent_id": self._agent_id or "unknown",
                        "model": self._model_name or "gemini-2.5-flash",
                        "usage": {
                            "input": int(task.input_tokens or 0),
                            "output": int(task.output_tokens or 0)
                        },
                        "latency_ms": float(0.0),
                        "timestamp": float(time.time())
                    })
                except Exception as exc:
                    self._logger.warning("Failed to dispatch telemetry: %s", exc)
            self._logger.info("api_call_complete name=%s", call_name)
            task.done.set()

    def execute(
        self,
        api_call: Callable[..., Any],
        *args: Any,
        projected_cost_tokens: float = 0.0,
        input_tokens: int = 0,
        output_tokens: int = 0,
        **kwargs: Any,
    ) -> Any:
        call_name = getattr(api_call, "__name__", repr(api_call))
        self._logger.info("api_call_start name=%s", call_name)
        reserve_budget(self, float(projected_cost_tokens))
        task = Task(api_call=api_call, args=args, kwargs=kwargs, done=threading.Event())
        task.input_tokens, task.output_tokens = int(input_tokens), int(output_tokens)
        acquired, retry_after_seconds = self._traffic.try_acquire_slot()
        if acquired:
            try:
                self._run_task(task)
            finally:
                self._traffic.release_slot()
        else:
            try:
                self._traffic.enqueue(task)
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
