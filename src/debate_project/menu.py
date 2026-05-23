"""Interactive terminal menu helpers."""

from __future__ import annotations

import msvcrt
from typing import Sequence

UP_KEYS = {"H", "K", "w", "W"}
DOWN_KEYS = {"P", "M", "s", "S"}
SELECT_KEYS = {"\r", " "}
QUIT_KEYS = {"q", "Q"}


def move_index(index: int, key: str, option_count: int) -> int:
    """Return the next menu index for a pressed key."""
    if key in UP_KEYS:
        return (index - 1) % option_count
    if key in DOWN_KEYS:
        return (index + 1) % option_count
    return index


def _read_key() -> str:
    """Read a single menu key, collapsing Windows arrow-key prefixes."""
    key = msvcrt.getwch()
    if key in {"\x00", "\xe0"}:
        return msvcrt.getwch()
    return key


def _render(title: str, options: Sequence[str], selected: int) -> str:
    lines = [title, "Use arrow keys or W/S, Enter to confirm, Q to quit."]
    for index, option in enumerate(options):
        marker = ">" if index == selected else " "
        lines.append(f" {marker} {option}")
    return "\n".join(lines)


def choose_option(title: str, options: Sequence[str]) -> str:
    """Render a keyboard-driven menu and return the selected option."""
    selected = 0
    while True:
        print("\x1b[2J\x1b[H" + _render(title, options, selected), flush=True)
        key = _read_key()
        if key in SELECT_KEYS:
            return options[selected]
        if key in QUIT_KEYS:
            raise KeyboardInterrupt("Menu aborted by user")
        selected = move_index(selected, key, len(options))


def choose_rounds(max_rounds: int) -> int:
    """Render a bounded rounds picker using the same keyboard loop."""
    options = [f"{value} rounds" for value in range(1, max_rounds + 1)]
    return int(choose_option("Select debate length", options).split()[0])
