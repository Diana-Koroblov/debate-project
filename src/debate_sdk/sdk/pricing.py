"""Token usage parsing and Gemini cost reporting."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

TOKEN_RE = re.compile(
    r"token_usage_update input_tokens=(?P<input>\d+) "
    r"output_tokens=(?P<output>\d+) tracked_consumption=(?P<tracked>[0-9.]+)"
)


@dataclass(frozen=True)
class PricingRate:
    """Per-million-token pricing for a Gemini model."""

    input_per_million: float
    output_per_million: float
    source: str


RATES = {
    "gemini-1.5-pro": PricingRate(1.25, 5.0, "legacy Gemini 1.5 Pro published rates"),
    "gemini-2.5-pro": PricingRate(1.25, 10.0, "Gemini pricing page 2026-05-19"),
    "gemini-2.5-flash": PricingRate(0.30, 2.50, "Gemini pricing page 2026-05-19"),
    "gemini-2.5-flash-lite": PricingRate(0.10, 0.40, "Gemini pricing page 2026-05-19"),
}


def resolve_pricing(model_name: str) -> PricingRate:
    """Resolve pricing metadata for a configured Gemini model."""
    if model_name in RATES:
        return RATES[model_name]
    for name, rate in RATES.items():
        if model_name.startswith(name):
            return rate
    return RATES["gemini-2.5-flash"]


def parse_token_usage(log_dir: Path | str) -> dict[str, float]:
    """Read the latest cumulative token totals from gatekeeper log lines."""
    usage = {"input_tokens": 0.0, "output_tokens": 0.0, "tracked_consumption": 0.0}
    log_root = Path(log_dir)
    for path in sorted(log_root.glob("agent_logs_*.log")):
        for line in path.read_text(encoding="utf-8").splitlines():
            match = TOKEN_RE.search(line)
            if not match:
                continue
            usage = {
                "input_tokens": float(match.group("input")),
                "output_tokens": float(match.group("output")),
                "tracked_consumption": float(match.group("tracked")),
            }
    return usage


def build_cost_summary(model_name: str, log_dir: Path | str) -> dict[str, Any]:
    """Build a terminal-friendly and artifact-friendly cost summary."""
    usage = parse_token_usage(log_dir)
    rate = resolve_pricing(model_name)
    input_cost = usage["input_tokens"] / 1_000_000 * rate.input_per_million
    output_cost = usage["output_tokens"] / 1_000_000 * rate.output_per_million
    return {
        "model": model_name,
        "pricing": asdict(rate),
        "usage": usage,
        "costs": {
            "input_cost_usd": round(input_cost, 6),
            "output_cost_usd": round(output_cost, 6),
            "total_cost_usd": round(input_cost + output_cost, 6),
        },
    }


def write_cost_summary(
    summary: dict[str, Any],
    results_dir: Path | str,
    session_id: str,
) -> Path:
    """Persist the final economic summary into the results directory."""
    target_dir = Path(results_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / f"cost_summary_{session_id}.json"
    path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return path
