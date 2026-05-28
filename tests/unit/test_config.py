"""Tests for configuration loading and validation."""

import json

import pytest

from debate_sdk.shared.config import load_rate_limits, load_setup_config


def test_load_setup_config_valid(tmp_path):
    cfg_path = tmp_path / "setup.json"
    data = {
        "version": "1.00",
        "watchdog": {"timeout_seconds": 10, "check_interval_seconds": 2},
        "debate": {
            "rounds": 10,
            "model": "gemini",
            "pro_persona": "Pro Persona",
            "con_persona": "Con Persona"
        }
    }
    cfg_path.write_text(json.dumps(data), encoding="utf-8")

    config = load_setup_config(cfg_path)
    assert config["version"] == "1.00"
    assert config["watchdog"]["timeout_seconds"] == 10.0


def test_load_setup_config_invalid(tmp_path):
    cfg_path = tmp_path / "setup.json"
    data = {
        "version": "1.00",
        "watchdog": {"timeout_seconds": 0},
        "debate": {
            "rounds": 10,
            "model": "gemini",
            "pro_persona": "Pro Persona",
            "con_persona": "Con Persona"
        }
    }
    cfg_path.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(ValueError, match="watchdog.timeout_seconds"):
        load_setup_config(cfg_path)


def test_load_setup_config_missing_field(tmp_path):
    cfg_path = tmp_path / "setup.json"
    data = {"version": "1.00", "watchdog": {"timeout_seconds": 10}}
    cfg_path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="Missing required setup fields"):
        load_setup_config(cfg_path)


def test_load_setup_config_invalid_interval(tmp_path):
    cfg_path = tmp_path / "setup.json"
    data = {
        "version": "1.00",
        "watchdog": {"timeout_seconds": 10, "check_interval_seconds": 0},
        "debate": {
            "rounds": 10,
            "model": "gemini",
            "pro_persona": "Pro Persona",
            "con_persona": "Con Persona"
        }
    }
    cfg_path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="watchdog.check_interval_seconds"):
        load_setup_config(cfg_path)


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
    assert config["tokens_per_minute"] == 0.0
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

    with pytest.raises(ValueError, match="Rate limit config error"):
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


def test_load_rate_limits_invalid_tokens_per_minute_raises_value_error(tmp_path):
    cfg_path = tmp_path / "rate_limits.json"
    cfg_path.write_text(
        json.dumps(
            {
                "version": "1.00",
                "requests_per_minute": 10,
                "tokens_per_minute": -1,
                "concurrent_max": 2,
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="tokens_per_minute"):
        load_rate_limits(cfg_path)
