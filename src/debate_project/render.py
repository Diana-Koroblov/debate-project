"""Thread-safe terminal rendering primitives for the CLI."""

from __future__ import annotations

import sys
import threading
from typing import Any, TextIO

COLORS = {
    "pro_agent": "\x1b[38;5;42m",
    "con_agent": "\x1b[38;5;203m",
    "judge": "\x1b[38;5;81m",
    "system": "\x1b[38;5;220m",
    "reset": "\x1b[0m",
}
SPINNER = "|/-\\"


class ConsoleStream:
    """Serialize terminal writes across event and log streams."""

    def __init__(self, stream: TextIO | None = None) -> None:
        self._stream = stream or sys.stdout
        self._lock = threading.Lock()
        self._spinner_index = 0
        self._spinner_visible = False

    def tick(self, label: str = "Awaiting debate events") -> None:
        """Advance a single-line spinner without disturbing printed lines."""
        with self._lock:
            frame = SPINNER[self._spinner_index % len(SPINNER)]
            self._spinner_index += 1
            self._spinner_visible = True
            self._stream.write(f"\r{COLORS['system']}[{frame}] {label}{COLORS['reset']}")
            self._stream.flush()

    def line(self, text: str) -> None:
        """Print a full line, clearing the spinner first if needed."""
        with self._lock:
            if self._spinner_visible:
                self._stream.write("\r" + (" " * 80) + "\r")
                self._spinner_visible = False
            self._stream.write(text + "\n")
            self._stream.flush()

    def render_event(self, event: dict[str, Any]) -> None:
        """Render queue events with agent-specific styling."""
        event_type = event.get("type")
        if event_type == "argument":
            agent_id = event["agent_id"]
            payload = event["payload"]["text"]
            color = COLORS.get(agent_id, COLORS["system"])
            line = (
                f"{color}[{agent_id}] Round {event['round_number']}: "
                f"{payload}{COLORS['reset']}"
            )
            self.line(line)
            return
        if event_type == "final_judgment":
            winner = event["winner_id"]
            score = event["differential_score"]
            line = (
                f"{COLORS['judge']}[judge] Winner: {winner} | "
                f"Differential score: {score}{COLORS['reset']}"
            )
            self.line(line)

    def render_log(self, line: str) -> None:
        """Surface watchdog and queue runtime messages without breaking layout."""
        if "STALL DETECTED" in line or "TERMINATION" in line:
            self.line(f"{COLORS['system']}[watchdog] {line}{COLORS['reset']}")

    def render_costs(
        self,
        summary: dict[str, Any],
        artifact_path: str,
        transcript_path: str,
    ) -> None:
        """Render a compact token and cost breakdown table."""
        usage = summary["usage"]
        costs = summary["costs"]
        self.line("Token Cost Breakdown")
        self.line("Metric           | Value")
        self.line("-----------------|----------------")
        self.line(f"Input tokens     | {int(usage['input_tokens'])}")
        self.line(f"Output tokens    | {int(usage['output_tokens'])}")
        self.line(f"Input cost (USD) | {costs['input_cost_usd']:.6f}")
        self.line(f"Output cost (USD)| {costs['output_cost_usd']:.6f}")
        self.line(f"Total cost (USD) | {costs['total_cost_usd']:.6f}")
        self.line(f"Summary artifact | {artifact_path}")
        self.line(f"Transcript       | {transcript_path}")
