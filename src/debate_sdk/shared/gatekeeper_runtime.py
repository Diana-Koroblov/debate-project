"""Internal helpers for gatekeeper retry and task state."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass
class Task:
    api_call: Callable[..., Any]
    args: tuple[Any, ...]
    kwargs: dict[str, Any]
    done: Any
    result: Any = None
    error: Exception | None = None


def is_transient_error(exc: Exception) -> bool:
    status = getattr(exc, "status", None) or getattr(exc, "status_code", None)
    if isinstance(status, int) and (status == 429 or 500 <= status < 600):
        return True
    if isinstance(exc, (TimeoutError, ConnectionError)):
        return True
    message = str(exc)
    return any(token in message for token in ("429", "500", "502", "503", "504"))


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
            delay = backoff_base_seconds * (2**attempt)
            logger.warning("api_call_retry name=%s attempt=%s delay=%.3f", name, attempt + 1, delay)
            sleeper(delay)
            attempt += 1
