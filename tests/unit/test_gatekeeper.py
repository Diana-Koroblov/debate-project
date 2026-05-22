"""Tests for ApiGatekeeper singleton and execute behavior."""

import logging

import pytest

from debate_sdk.shared.gatekeeper import ApiGatekeeper


def setup_function():
    ApiGatekeeper.reset_instance()


def test_gatekeeper_is_singleton(tmp_path):
    cfg_path = tmp_path / "rate_limits.json"
    cfg_path.write_text(
        '{"version":"1.00","requests_per_minute":60,"concurrent_max":3}',
        encoding="utf-8",
    )

    first = ApiGatekeeper(cfg_path)
    second = ApiGatekeeper(cfg_path)

    assert first is second


def test_execute_returns_value_and_logs_start_and_complete(tmp_path, caplog):
    cfg_path = tmp_path / "rate_limits.json"
    cfg_path.write_text(
        '{"version":"1.00","requests_per_minute":60,"concurrent_max":3}',
        encoding="utf-8",
    )
    gatekeeper = ApiGatekeeper(cfg_path)

    def fake_call(value):
        return value * 2

    with caplog.at_level(logging.INFO):
        result = gatekeeper.execute(fake_call, 4)

    assert result == 8
    joined = "\n".join(caplog.messages)
    assert "api_call_start" in joined
    assert "api_call_success" in joined
    assert "api_call_complete" in joined


def test_execute_reraises_and_logs_failure(tmp_path, caplog):
    cfg_path = tmp_path / "rate_limits.json"
    cfg_path.write_text(
        '{"version":"1.00","requests_per_minute":60,"concurrent_max":3}',
        encoding="utf-8",
    )
    gatekeeper = ApiGatekeeper(cfg_path)

    def fake_call_error():
        raise ValueError("boom")

    with caplog.at_level(logging.INFO), pytest.raises(RuntimeError, match="API call"):
        gatekeeper.execute(fake_call_error)

    joined = "\n".join(caplog.messages)
    assert "api_call_failure" in joined
    assert "api_call_complete" in joined


def test_execute_retries_transient_error_with_exponential_backoff(tmp_path):
    cfg_path = tmp_path / "rate_limits.json"
    cfg_path.write_text(
        (
            "{"
            '"version":"1.00",'
            '"requests_per_minute":60,'
            '"concurrent_max":3,'
            '"max_retries":3,'
            '"backoff_base_seconds":0.5'
            "}"
        ),
        encoding="utf-8",
    )
    delays = []

    gatekeeper = ApiGatekeeper(cfg_path, sleeper=lambda seconds: delays.append(seconds))
    attempts = {"count": 0}

    def flaky_call():
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise RuntimeError("503 service unavailable")
        return "ok"

    assert gatekeeper.execute(flaky_call) == "ok"
    assert delays == [0.5, 1.0]
