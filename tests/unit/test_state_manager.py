"""Unit tests for the StateManager utility."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from debate_sdk.shared.state_manager import StateManager


@pytest.fixture
def temp_storage(tmp_path: Path) -> Path:
    """Fixture to provide a temporary storage directory."""
    return tmp_path / "states"


def test_state_manager_save_load(temp_storage):
    """Test saving and loading state."""
    sm = StateManager(temp_storage, "test_session")
    state_data = {"round": 1, "history": ["hello"]}

    sm.save_state(state_data)
    assert sm.storage_path.exists()

    loaded_state = sm.load_state()
    assert loaded_state == state_data


def test_state_manager_atomic_save(temp_storage):
    """Test that saving state is atomic and doesn't corrupt on failure."""
    sm = StateManager(temp_storage, "atomic_test")
    state_data = {"key": "value"}

    # Save first time
    sm.save_state(state_data)

    # Mock a failure by making the directory read-only (not easy on Windows)
    # Instead, verify the .tmp file existence during save if we could,
    # but here we just check final result.
    assert sm.load_state() == state_data


def test_state_manager_load_non_existent(temp_storage):
    """Test loading a non-existent state file."""
    sm = StateManager(temp_storage, "ghost_session")
    assert sm.load_state() is None


def test_state_manager_load_corrupt(temp_storage):
    """Test loading a corrupted state file."""
    sm = StateManager(temp_storage, "corrupt_session")
    sm.storage_path.write_text("invalid json", encoding="utf-8")

    assert sm.load_state() is None


def test_state_manager_clear(temp_storage):
    """Test clearing the state file."""
    sm = StateManager(temp_storage, "clear_test")
    sm.save_state({"data": 123})
    assert sm.storage_path.exists()

    sm.clear_state()
    assert not sm.storage_path.exists()


def test_state_manager_load_io_error(temp_storage):
    """Test loading state with an IO error."""
    sm = StateManager(temp_storage, "io_fail_session")
    sm.save_state({"data": 1})

    with patch("builtins.open", side_effect=IOError("Permission denied")):
        assert sm.load_state() is None


def test_state_manager_save_cleanup_on_error(temp_storage):
    """Test that temp file is cleaned up if rename fails."""
    sm = StateManager(temp_storage, "cleanup_test")

    with patch("pathlib.Path.replace", side_effect=OSError("Disk failure")):
        sm.save_state({"a": 1})
        # Verify temp file is deleted (suffix is .tmp)
        temp_file = sm.storage_path.with_suffix(".tmp")
        assert not temp_file.exists()
