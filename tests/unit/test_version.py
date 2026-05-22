"""Version contract tests."""

from debate_sdk.shared.version import __version__


def test_version_string_matches_phase_one_contract() -> None:
    assert __version__ == "1.00"
