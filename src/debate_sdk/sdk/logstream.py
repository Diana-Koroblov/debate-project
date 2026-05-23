"""Helpers for following rotating runtime log files."""

from __future__ import annotations

import time
from pathlib import Path
from threading import Event
from typing import Callable


def follow_logs(
    log_dir: Path | str,
    stop_event: Event,
    on_line: Callable[[str], None],
    *,
    poll_interval: float = 0.1,
) -> None:
    """Stream appended log lines until stopped."""
    positions: dict[Path, int] = {}
    root = Path(log_dir)
    while not stop_event.is_set():
        for path in sorted(root.glob("agent_logs_*.log")):
            previous = positions.get(path, 0)
            text = path.read_text(encoding="utf-8")
            positions[path] = len(text)
            if len(text) <= previous:
                continue
            for line in text[previous:].splitlines():
                on_line(line)
        time.sleep(poll_interval)
