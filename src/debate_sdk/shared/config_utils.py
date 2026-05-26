"""Utilities for normalizing configuration objects."""

from __future__ import annotations

from typing import Any

REQ_RATE_FIELDS = ("version", "requests_per_minute", "concurrent_max")
REQ_LOG_FIELDS = ("version", "log_directory", "max_files", "max_lines_per_file")
REQ_SETUP_FIELDS = ("version", "watchdog", "debate")


def normalize_setup_config(raw: dict[str, Any]) -> dict[str, Any]:
    missing = [f for f in REQ_SETUP_FIELDS if f not in raw]
    if missing:
        raise ValueError(f"Missing required setup fields: {', '.join(missing)}")

    wd = raw["watchdog"]
    t_sec = wd.get("timeout_seconds")
    c_int = wd.get("check_interval_seconds")

    if not isinstance(t_sec, (int, float)) or t_sec <= 0:
        raise ValueError("watchdog.timeout_seconds must be a positive number")
    if not isinstance(c_int, (int, float)) or c_int <= 0:
        raise ValueError("watchdog.check_interval_seconds must be a positive number")

    debate = raw["debate"]
    if not isinstance(debate, dict):
        raise ValueError("Field 'debate' must be a JSON object")

    for field in ("rounds", "model", "pro_persona", "con_persona"):
        if field not in debate:
            raise ValueError(f"Missing required debate field: {field}")

    if not isinstance(debate["rounds"], int) or debate["rounds"] <= 0:
        raise ValueError("debate.rounds must be a positive integer")

    return {
        "version": raw["version"],
        "watchdog": {
            "timeout_seconds": float(t_sec),
            "check_interval_seconds": float(c_int),
        },
        "debate": debate,
    }


def normalize_logging_config(raw: dict[str, Any]) -> dict[str, Any]:
    missing = [f for f in REQ_LOG_FIELDS if f not in raw]
    if missing:
        raise ValueError(f"Missing required logging fields: {', '.join(missing)}")

    m_files, m_lines = raw["max_files"], raw["max_lines_per_file"]
    if not isinstance(m_files, int) or m_files <= 0:
        raise ValueError("Field 'max_files' must be a positive integer")
    if not isinstance(m_lines, int) or m_lines <= 0:
        raise ValueError("Field 'max_lines_per_file' must be a positive integer")

    return {
        "version": raw["version"],
        "log_directory": raw["log_directory"],
        "max_files": m_files,
        "max_lines_per_file": m_lines,
        "log_level": raw.get("log_level", "INFO"),
    }


def normalize_rate_limit_config(raw: dict[str, Any]) -> dict[str, Any]:
    missing = [f for f in REQ_RATE_FIELDS if f not in raw]
    if missing:
        raise ValueError(f"Missing required rate limit fields: {', '.join(missing)}")

    ver, rpm, cmax = raw["version"], raw["requests_per_minute"], raw["concurrent_max"]
    if not isinstance(ver, str) or not ver.strip():
        raise ValueError("Field 'version' must be a non-empty string")
    if not isinstance(rpm, int) or rpm <= 0:
        raise ValueError("Field 'requests_per_minute' must be a positive integer")
    if not isinstance(cmax, int) or cmax <= 0:
        raise ValueError("Field 'concurrent_max' must be a positive integer")

    q_max = raw.get("queue_max_size", 100)
    m_ret = raw.get("max_retries", 3)
    b_base = raw.get("backoff_base_seconds", 0.25)
    m_bud = raw.get("max_budget_tokens", 100000)

    if not isinstance(q_max, int) or q_max <= 0:
        raise ValueError("Field 'queue_max_size' must be a positive integer")
    if not isinstance(m_ret, int) or m_ret < 0:
        raise ValueError("Field 'max_retries' must be a non-negative integer")
    if not isinstance(b_base, (int, float)) or b_base <= 0:
        raise ValueError("Field 'backoff_base_seconds' must be a positive number")
    if not isinstance(m_bud, (int, float)) or m_bud <= 0:
        raise ValueError("Field 'max_budget_tokens' must be a positive number")

    return {
        "version": ver, "requests_per_minute": rpm, "concurrent_max": cmax,
        "queue_max_size": q_max, "max_retries": m_ret,
        "backoff_base_seconds": float(b_base), "max_budget_tokens": float(m_bud),
    }
