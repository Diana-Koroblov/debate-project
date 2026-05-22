"""Tests for gatekeeper throttling, queue overflow, and retry-after behavior."""

from debate_sdk.shared.gatekeeper import ApiGatekeeper


def setup_function():
    ApiGatekeeper.reset_instance()


class FakeClock:
    def __init__(self):
        self.value = 0.0

    def now(self):
        return self.value

    def sleep(self, seconds):
        self.value += seconds


def test_retry_after_seconds_is_positive_when_rate_limit_is_exhausted(tmp_path):
    cfg_path = tmp_path / "rate_limits.json"
    cfg_path.write_text(
        (
            "{"
            '"version":"1.00",'
            '"requests_per_minute":1,'
            '"concurrent_max":1'
            "}"
        ),
        encoding="utf-8",
    )
    clock = FakeClock()
    gatekeeper = ApiGatekeeper(cfg_path, time_fn=clock.now, sleeper=clock.sleep)

    assert gatekeeper.execute(lambda: "first") == "first"
    assert gatekeeper._retry_after_seconds() >= 59.0


def test_rate_limited_call_gets_queued_and_dispatched_after_window(tmp_path):
    cfg_path = tmp_path / "rate_limits.json"
    cfg_path.write_text(
        (
            "{"
            '"version":"1.00",'
            '"requests_per_minute":1,'
            '"concurrent_max":1,'
            '"queue_max_size":2,'
            '"max_retries":0,'
            '"backoff_base_seconds":0.1'
            "}"
        ),
        encoding="utf-8",
    )
    clock = FakeClock()
    gatekeeper = ApiGatekeeper(cfg_path, time_fn=clock.now, sleeper=clock.sleep)

    assert gatekeeper.execute(lambda: "first") == "first"
    assert gatekeeper.execute(lambda: "second") == "second"
    assert clock.value >= 60.0


def test_queue_overflow_raises_runtime_error(tmp_path, monkeypatch):
    cfg_path = tmp_path / "rate_limits.json"
    cfg_path.write_text(
        (
            "{"
            '"version":"1.00",'
            '"requests_per_minute":60,'
            '"concurrent_max":1,'
            '"queue_max_size":1'
            "}"
        ),
        encoding="utf-8",
    )
    gatekeeper = ApiGatekeeper(cfg_path)

    gatekeeper._queue.put_nowait(object())
    monkeypatch.setattr(gatekeeper, "_try_acquire_slot", lambda: (False, 1.0))

    try:
        gatekeeper.execute(lambda: "value")
        assert False, "Expected queue overflow RuntimeError"
    except RuntimeError as exc:
        assert "overflow queue" in str(exc)
