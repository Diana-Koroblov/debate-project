from __future__ import annotations

from typing import Any

from debate_sdk.shared.exceptions import BudgetExceededException
from debate_sdk.shared.gatekeeper_runtime import Task, derive_usage_from_result


def token_usage_snapshot(gatekeeper: object) -> dict[str, float]:
    return {
        "input_tokens": float(gatekeeper._input_tokens_total),
        "output_tokens": float(gatekeeper._output_tokens_total),
        "tracked_consumption": gatekeeper._tracked_token_consumption,
        "max_budget_tokens": gatekeeper._max_budget_tokens,
    }


def reserve_budget(gatekeeper: object, projected_cost: float) -> None:
    with gatekeeper._budget_lock:
        projected_total = gatekeeper._tracked_token_consumption + projected_cost
        if projected_total > gatekeeper._max_budget_tokens:
            raise BudgetExceededException("Projected token cost exceeds budget limit")
        gatekeeper._tracked_token_consumption = projected_total


def record_usage(gatekeeper: Any, task: Task) -> None:
    derived_input, derived_output = derive_usage_from_result(task.result)
    with gatekeeper._budget_lock:
        gatekeeper._input_tokens_total += max(task.input_tokens, derived_input)
        gatekeeper._output_tokens_total += max(task.output_tokens, derived_output)
        gatekeeper._logger.info(
            "token_usage_update input_tokens=%s output_tokens=%s tracked_consumption=%s",
            gatekeeper._input_tokens_total,
            gatekeeper._output_tokens_total,
            gatekeeper._tracked_token_consumption,
        )
