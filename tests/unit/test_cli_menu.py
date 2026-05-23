"""Tests for keyboard menu helpers."""

from debate_project.menu import move_index


def test_move_index_wraps_upward() -> None:
    assert move_index(0, "H", 3) == 2


def test_move_index_wraps_downward() -> None:
    assert move_index(2, "P", 3) == 0


def test_move_index_ignores_unhandled_keys() -> None:
    assert move_index(1, "x", 3) == 1
