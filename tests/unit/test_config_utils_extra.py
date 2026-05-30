import pytest

from debate_sdk.shared.config_utils import normalize_rate_limit_config


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ({"version": "", "requests_per_minute": 1, "concurrent_max": 1}, "version"),
        ({"version": "1.00", "requests_per_minute": 0, "concurrent_max": 1}, "requests_per_minute"),
        ({"version": "1.00", "requests_per_minute": 1, "concurrent_max": 0}, "concurrent_max"),
        ({"version": "1.00", "requests_per_minute": 1, "concurrent_max": 1, "queue_max_size": 0}, "queue_max_size"),
        ({"version": "1.00", "requests_per_minute": 1, "concurrent_max": 1, "max_retries": -1}, "max_retries"),
        ({"version": "1.00", "requests_per_minute": 1, "concurrent_max": 1, "backoff_base_seconds": 0}, "backoff_base_seconds"),
    ],
)
def test_normalize_rate_limit_config_rejects_invalid_scalar_values(payload, message):
    with pytest.raises(ValueError, match=message):
        normalize_rate_limit_config(payload)