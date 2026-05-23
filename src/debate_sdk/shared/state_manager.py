"""State management and session recovery utilities."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from debate_sdk.shared.logger import setup_logger

logger = setup_logger("state_manager")


class StateManager:
    """
    Handles persistence and recovery of the debate session state.

    Attributes:
        storage_path (Path): File path where state is serialized.
    """

    def __init__(self, storage_dir: str | Path, session_id: str) -> None:
        """
        Initialize the StateManager.

        Args:
            storage_dir (str | Path): Directory for state files.
            session_id (str): Unique session identifier.
        """
        self.storage_path = Path(storage_dir) / f"session_{session_id}.state"
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

    def save_state(self, state: Dict[str, Any]) -> None:
        """
        Atomically save the current debate state to disk.

        Args:
            state (Dict[str, Any]): Dictionary containing session data.
        """
        temp_path = self.storage_path.with_suffix(".tmp")
        try:
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2)

            # Atomic rename to prevent corruption during writes
            temp_path.replace(self.storage_path)
            logger.debug(f"State saved to {self.storage_path}")
        except Exception as exc:
            logger.error(f"Failed to save state: {exc}")
            if temp_path.exists():
                temp_path.unlink()

    def load_state(self) -> Dict[str, Any] | None:
        """
        Load the latest valid state from disk.

        Returns:
            Dict[str, Any] | None: The loaded state or None if no valid state exists.
        """
        if not self.storage_path.exists():
            logger.warning(f"No state file found at {self.storage_path}")
            return None

        try:
            with open(self.storage_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as exc:
            logger.error(f"Failed to load state from {self.storage_path}: {exc}")
            return None

    def clear_state(self) -> None:
        """Remove the state file from disk."""
        if self.storage_path.exists():
            self.storage_path.unlink()
            logger.info(f"Cleared state file {self.storage_path}")
