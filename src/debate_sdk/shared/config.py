"""Configuration loading and validation utilities."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

REQUIRED_RATE_LIMIT_FIELDS = ("version", "requests_per_minute", "concurrent_max")


def _project_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _normalize_rate_limit_config(raw: dict[str, Any]) -> dict[str, Any]:
    missing = [field for field in REQUIRED_RATE_LIMIT_FIELDS if field not in raw]
    if missing:
        missing_fields = ", ".join(missing)
        raise ValueError(f"Missing required rate limit fields: {missing_fields}")

    version = raw["version"]
    requests_per_minute = raw["requests_per_minute"]
    concurrent_max = raw["concurrent_max"]

    if not isinstance(version, str) or not version.strip():
        raise ValueError("Field 'version' must be a non-empty string")
    if not isinstance(requests_per_minute, int) or requests_per_minute <= 0:
        raise ValueError("Field 'requests_per_minute' must be a positive integer")
    if not isinstance(concurrent_max, int) or concurrent_max <= 0:
        raise ValueError("Field 'concurrent_max' must be a positive integer")

    queue_max_size = raw.get("queue_max_size", 100)
    max_retries = raw.get("max_retries", 3)
    backoff_base_seconds = raw.get("backoff_base_seconds", 0.25)
    if not isinstance(queue_max_size, int) or queue_max_size <= 0:
        raise ValueError("Field 'queue_max_size' must be a positive integer")
    if not isinstance(max_retries, int) or max_retries < 0:
        raise ValueError("Field 'max_retries' must be a non-negative integer")
    if not isinstance(backoff_base_seconds, (int, float)) or backoff_base_seconds <= 0:
        raise ValueError("Field 'backoff_base_seconds' must be a positive number")

    return {
        "version": version,
        "requests_per_minute": requests_per_minute,
        "concurrent_max": concurrent_max,
        "queue_max_size": queue_max_size,
        "max_retries": max_retries,
        "backoff_base_seconds": float(backoff_base_seconds),
    }


def load_rate_limits(config_path: Path | str | None = None) -> dict[str, Any]:
    """Load and validate API rate limit configuration from JSON."""
    path = Path(config_path) if config_path else _project_root() / "config" / "rate_limits.json"
    try:
        raw_config = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"Rate limit config file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in rate limit config: {path}") from exc

    if not isinstance(raw_config, dict):
        raise ValueError("Rate limit config root must be a JSON object")

    return _normalize_rate_limit_config(raw_config)
