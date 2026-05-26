from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from debate_sdk.shared.gatekeeper_runtime import retry_delay_seconds, run_with_retries


def test_retry_delay_seconds_uses_provider_hint() -> None:
    exc = RuntimeError("503 service unavailable. Please retry in 20.86226464s.")
    delay = retry_delay_seconds(exc, attempt=0, backoff_base_seconds=0.25)
    assert delay == pytest.approx(20.86226464)


def test_run_with_retries_waits_for_provider_delay() -> None:
    attempts = {"count": 0}
    waits: list[float] = []

    def flaky_call() -> str:
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise RuntimeError("503 service unavailable. Please retry in 3.5s.")
        return "ok"

    result = run_with_retries(
        flaky_call,
        logger=MagicMock(),
        sleeper=waits.append,
        max_retries=3,
        backoff_base_seconds=0.25,
    )

    assert result == "ok"
    assert waits == [3.5]


def test_run_with_retries_fails_immediately_on_quota_error() -> None:
    waits: list[float] = []

    def quota_fails() -> None:
        raise RuntimeError("429 quota exceeded")

    with pytest.raises(RuntimeError, match="429 quota exceeded"):
        run_with_retries(
            quota_fails,
            logger=MagicMock(),
            sleeper=waits.append,
            max_retries=3,
            backoff_base_seconds=0.25,
        )

    assert len(waits) == 0


def test_run_with_retries_uses_exponential_backoff_without_hint() -> None:
    waits: list[float] = []

    def always_fails() -> None:
        raise RuntimeError("503 service unavailable")

    with pytest.raises(RuntimeError, match="API call 'always_fails' failed"):
        run_with_retries(
            always_fails,
            logger=MagicMock(),
            sleeper=waits.append,
            max_retries=2,
            backoff_base_seconds=0.25,
        )

    assert waits == [0.25, 0.5]
