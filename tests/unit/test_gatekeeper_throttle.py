"""Tests for gatekeeper throttling, queue overflow, and retry-after behavior."""

from queue import Full

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
    assert gatekeeper._traffic.retry_after_seconds() >= 59.0


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


def test_token_limited_call_gets_queued_until_tokens_expire(tmp_path):
    cfg_path = tmp_path / "rate_limits.json"
    cfg_path.write_text(
        (
            "{"
            '"version":"1.00",'
            '"requests_per_minute":60,'
            '"tokens_per_minute":6000,'
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

    assert gatekeeper.execute(lambda: "first", projected_cost_tokens=2000) == "first"
    assert gatekeeper.execute(lambda: "second", projected_cost_tokens=2000) == "second"
    assert gatekeeper.execute(lambda: "third", projected_cost_tokens=2000) == "third"
    assert gatekeeper.execute(lambda: "fourth", projected_cost_tokens=2000) == "fourth"
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

    monkeypatch.setattr(gatekeeper._traffic, "try_acquire_slot", lambda _projected_cost=0.0: (False, 1.0))
    monkeypatch.setattr(gatekeeper._traffic, "enqueue", lambda _task: (_ for _ in ()).throw(Full()))

    try:
        gatekeeper.execute(lambda: "value")
        assert False, "Expected queue overflow RuntimeError"
    except RuntimeError as exc:
        assert "overflow queue" in str(exc)
