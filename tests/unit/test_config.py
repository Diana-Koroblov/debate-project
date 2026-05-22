"""Tests for configuration loading and validation."""

import json

import pytest

from debate_sdk.shared.config import load_rate_limits


def test_load_rate_limits_valid_file(tmp_path):
    cfg_path = tmp_path / "rate_limits.json"
    cfg_path.write_text(
        json.dumps(
            {
                "version": "1.00",
                "requests_per_minute": 10,
                "concurrent_max": 2,
            }
        ),
        encoding="utf-8",
    )

    config = load_rate_limits(cfg_path)

    assert config["version"] == "1.00"
    assert config["requests_per_minute"] == 10
    assert config["concurrent_max"] == 2


def test_load_rate_limits_missing_field_raises_value_error(tmp_path):
    cfg_path = tmp_path / "rate_limits.json"
    cfg_path.write_text(
        json.dumps({"version": "1.00", "requests_per_minute": 10}),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Missing required rate limit fields"):
        load_rate_limits(cfg_path)


def test_load_rate_limits_invalid_json_raises_value_error(tmp_path):
    cfg_path = tmp_path / "rate_limits.json"
    cfg_path.write_text("{not-valid-json", encoding="utf-8")

    with pytest.raises(ValueError, match="Invalid JSON"):
        load_rate_limits(cfg_path)


def test_load_rate_limits_invalid_budget_raises_value_error(tmp_path):
    cfg_path = tmp_path / "rate_limits.json"
    cfg_path.write_text(
        json.dumps(
            {
                "version": "1.00",
                "requests_per_minute": 10,
                "concurrent_max": 2,
                "max_budget_tokens": 0,
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="max_budget_tokens"):
        load_rate_limits(cfg_path)
