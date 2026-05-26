"""Configuration loading and validation utilities."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from debate_sdk.shared.config_utils import (
    normalize_logging_config,
    normalize_rate_limit_config,
    normalize_setup_config,
)


def _project_root() -> Path:
    return Path(__file__).resolve().parents[3]


def load_setup_config(config_path: Path | str | None = None) -> dict[str, Any]:
    """Load and validate general setup configuration from JSON."""
    p = Path(config_path) if config_path else _project_root() / "config" / "setup.json"
    try:
        raw_config = json.loads(p.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        raise ValueError(f"Setup config error at {p}: {exc}") from exc

    if not isinstance(raw_config, dict):
        raise ValueError("Setup config root must be a JSON object")

    return normalize_setup_config(raw_config)


def load_logging_config(config_path: Path | str | None = None) -> dict[str, Any]:
    """Load and validate logging configuration from JSON."""
    path = Path(config_path) if config_path else _project_root() / "config" / "logging_config.json"
    try:
        raw_config = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        raise ValueError(f"Logging config error at {path}: {exc}") from exc

    if not isinstance(raw_config, dict):
        raise ValueError("Logging config root must be a JSON object")

    return normalize_logging_config(raw_config)


def load_rate_limits(config_path: Path | str | None = None) -> dict[str, Any]:
    """Load and validate API rate limit configuration from JSON."""
    p = Path(config_path) if config_path else _project_root() / "config" / "rate_limits.json"
    try:
        raw_config = json.loads(p.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        raise ValueError(f"Rate limit config error at {p}: {exc}") from exc

    if not isinstance(raw_config, dict):
        raise ValueError("Rate limit config root must be a JSON object")

    return normalize_rate_limit_config(raw_config)
