"""SDK runner for debate sessions and live event streaming."""

from __future__ import annotations

import multiprocessing
import queue
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from debate_sdk.sdk.pricing import build_cost_summary, write_cost_summary
from debate_sdk.services.child_agent import ChildDebaterAgent
from debate_sdk.services.con_agent import ConDebaterAgent
from debate_sdk.services.judge_agent import ParentJudgeAgent
from debate_sdk.services.pro_agent import ProDebaterAgent
from debate_sdk.shared.config import load_logging_config, load_setup_config

EventHandler = Callable[[dict[str, Any]], None]
IdleHandler = Callable[[], None]


@dataclass(frozen=True)
class DebateSessionOptions:
    """User-selectable session parameters."""

    rounds: int
    session_id: str | None = None


@dataclass(frozen=True)
class DebateSessionResult:
    """Final session outcome and cost artifact metadata."""

    final_judgment: dict[str, Any]
    cost_summary: dict[str, Any]
    artifact_path: Path


def session_round_limit() -> int:
    """Maximum selectable rounds exposed by the CLI."""
    configured = int(load_setup_config()["debate"]["rounds"])
    return max(1, min(configured, 10))


def build_session_config(options: DebateSessionOptions) -> dict[str, Any]:
    """Load setup.json and merge bounded runtime options."""
    config = load_setup_config()
    rounds = max(1, min(options.rounds, session_round_limit()))
    return {
        **config,
        "session_id": options.session_id or f"cli-{uuid.uuid4().hex[:8]}",
        "storage_dir": "results/state",
        "stream_events": True,
        "debate": {**config["debate"], "rounds": rounds},
    }


def _judge_worker(
    judge_cls: type[ParentJudgeAgent],
    config: dict[str, Any],
    inbound: multiprocessing.Queue,
    outbound: multiprocessing.Queue,
    pro_cls: type[ChildDebaterAgent],
    con_cls: type[ChildDebaterAgent],
) -> None:
    judge = judge_cls("judge_cli", config, inbound, outbound)
    judge.spawn_children(pro_cls=pro_cls, con_cls=con_cls)
    judge.start_debate()
    judge.run()
    judge.terminate_children()


def run_debate_session(
    options: DebateSessionOptions,
    *,
    on_event: EventHandler | None = None,
    on_idle: IdleHandler | None = None,
    judge_cls: type[ParentJudgeAgent] = ParentJudgeAgent,
    pro_cls: type[ChildDebaterAgent] = ProDebaterAgent,
    con_cls: type[ChildDebaterAgent] = ConDebaterAgent,
) -> DebateSessionResult:
    """Execute a debate session and stream queue events to optional callbacks."""
    config = build_session_config(options)
    inbound: multiprocessing.Queue = multiprocessing.Queue()
    outbound: multiprocessing.Queue = multiprocessing.Queue()
    worker = multiprocessing.Process(
        target=_judge_worker,
        args=(judge_cls, config, inbound, outbound, pro_cls, con_cls),
        daemon=True,
    )
    worker.start()
    final_judgment: dict[str, Any] | None = None
    try:
        while worker.is_alive() or not outbound.empty():
            try:
                event = outbound.get(timeout=0.1)
            except queue.Empty:
                if on_idle:
                    on_idle()
                continue
            if isinstance(event, dict) and on_event:
                on_event(event)
            if isinstance(event, dict) and event.get("type") == "final_judgment":
                final_judgment = event
                break
        worker.join(timeout=5)
    finally:
        if worker.is_alive():
            worker.terminate()
            worker.join(timeout=5)
    if final_judgment is None:
        raise RuntimeError("Debate session ended without a final judgment")
    log_dir = load_logging_config()["log_directory"]
    cost_summary = build_cost_summary(config["debate"]["model"], log_dir)
    artifact_path = write_cost_summary(cost_summary, "results", config["session_id"])
    return DebateSessionResult(final_judgment, cost_summary, artifact_path)
