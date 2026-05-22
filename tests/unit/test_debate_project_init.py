"""Tests for the generated top-level package module."""

from debate_project import hello


def test_hello_returns_expected_message() -> None:
    assert hello() == "Hello from debate-project!"
