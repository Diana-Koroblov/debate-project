"""Token usage parsing and Gemini cost reporting."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


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


def build_cost_summary(
    model_name: str,
    usage: dict[str, float]
) -> dict[str, Any]:
    """Build a terminal-friendly and artifact-friendly cost summary."""
    rate = resolve_pricing(model_name)
    input_tokens = usage.get("input_tokens", 0.0)
    output_tokens = usage.get("output_tokens", 0.0)

    input_cost = input_tokens / 1_000_000 * rate.input_per_million
    output_cost = output_tokens / 1_000_000 * rate.output_per_million

    return {
        "model": model_name,
        "pricing": asdict(rate),
        "usage": {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "tracked_consumption": usage.get("tracked_consumption", 0.0)
        },
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
