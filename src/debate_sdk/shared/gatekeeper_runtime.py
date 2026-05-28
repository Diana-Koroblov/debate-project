"""Internal helpers for gatekeeper retry and task state."""

from __future__ import annotations

import re
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

RETRY_DELAY_RE = re.compile(
    r"(?:retry|try again) in (?P<value>\d+(?:\.\d+)?)(?P<unit>ms|s)",
    re.IGNORECASE,
)


@dataclass
class Task:
    api_call: Callable[..., Any]
    args: tuple[Any, ...]
    kwargs: dict[str, Any]
    done: Any
    projected_cost: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    result: Any = None
    error: Exception | None = None


def dispatch_telemetry(
    logger: Any,
    outbound_queue: Any,
    agent_id: str | None,
    model_name: str | None,
    task: Task,
) -> None:
    if outbound_queue is None:
        return
    try:
        outbound_queue.put_nowait({
            "type": "telemetry",
            "agent_id": agent_id or "unknown",
            "model": model_name or "llama-3.1-8b-instant",
            "usage": {
                "input": int(task.input_tokens or 0),
                "output": int(task.output_tokens or 0)
            },
            "latency_ms": float(0.0),
            "timestamp": float(time.time())
        })
    except Exception as exc:
        logger.warning("Failed to dispatch telemetry: %s", exc)


def ensure_version_compatibility(config_version: str, expected_version: str, logger: Any) -> None:
    if config_version == expected_version:
        return
    logger.warning(
        "rate_limit_config_version_mismatch expected=%s found=%s",
        expected_version,
        config_version,
    )
    message = (
        "Rate limit config version mismatch: "
        f"expected '{expected_version}', found '{config_version}'"
    )
    raise ValueError(
        message
    )


def derive_usage_from_result(result: Any) -> tuple[int, int]:
    if not isinstance(result, dict):
        return 0, 0
    if isinstance(result.get("usage"), dict):
        usage = result["usage"]
        return int(usage.get("input", 0)), int(usage.get("output", 0))
    return int(result.get("input_tokens", 0)), int(result.get("output_tokens", 0))


def is_transient_error(exc: Exception) -> bool:
    status = getattr(exc, "status", None) or getattr(exc, "status_code", None)
    message = str(exc).lower()

    if (isinstance(status, int) and status == 429) or "quota" in message or "429" in message:
        return RETRY_DELAY_RE.search(str(exc)) is not None

    if isinstance(status, int) and (500 <= status < 600):
        return True
    if isinstance(exc, (TimeoutError, ConnectionError)):
        return True
    return any(token in message for token in ("500", "502", "503", "504"))


def retry_delay_seconds(exc: Exception, attempt: int, backoff_base_seconds: float) -> float:
    delay = backoff_base_seconds * (2**attempt)
    match = RETRY_DELAY_RE.search(str(exc))
    if not match:
        return delay
    value = float(match.group("value"))
    if match.group("unit").lower() == "ms":
        value /= 1000.0
    return max(delay, value)


def run_with_retries(
    api_call: Callable[..., Any],
    logger: Any,
    sleeper: Callable[[float], None],
    max_retries: int,
    backoff_base_seconds: float,
    *args: Any,
    **kwargs: Any,
) -> Any:
    attempt = 0
    name = getattr(api_call, "__name__", repr(api_call))
    while True:
        try:
            return api_call(*args, **kwargs)
        except Exception as exc:
            if not is_transient_error(exc) or attempt >= max_retries:
                raise RuntimeError(f"API call '{name}' failed: {exc}") from None
            delay = retry_delay_seconds(exc, attempt, backoff_base_seconds)
            logger.warning("api_call_retry name=%s attempt=%s delay=%.3f", name, attempt + 1, delay)
            sleeper(delay)
            attempt += 1
