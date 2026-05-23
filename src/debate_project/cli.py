"""Command-line entry point for running debates."""

from __future__ import annotations

from threading import Event, Thread

from debate_project.menu import choose_option, choose_rounds
from debate_project.render import ConsoleStream
from debate_sdk.sdk.logstream import follow_logs
from debate_sdk.sdk.session import DebateSessionOptions, run_debate_session, session_round_limit
from debate_sdk.shared.config import load_logging_config


def main() -> int:
    """Run the interactive CLI workflow."""
    console = ConsoleStream()
    action = choose_option("Debate Project", ["Start debate", "Quit"])
    if action == "Quit":
        return 0

    max_rounds = session_round_limit()
    rounds = choose_rounds(max_rounds)
    stop_event = Event()
    log_thread = Thread(
        target=follow_logs,
        args=(load_logging_config()["log_directory"], stop_event, console.render_log),
        daemon=True,
    )
    log_thread.start()
    try:
        result = run_debate_session(
            DebateSessionOptions(rounds=rounds),
            on_event=console.render_event,
            on_idle=console.tick,
        )
    finally:
        stop_event.set()
        log_thread.join(timeout=1)
    console.render_costs(result.cost_summary, str(result.artifact_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
