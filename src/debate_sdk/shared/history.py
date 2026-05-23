"""In-memory history ledger for tracking debate turns."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Dict, List

from debate_sdk.shared.contracts import ChildToParentMessage


class HistoryLedger:
    """
    Chronological ledger of all debate transactions.

    This class manages the in-memory state of the conversation,
    ensuring all entries are sanitized and properly formatted.
    """

    def __init__(self) -> None:
        """Initialize an empty ledger."""
        self.entries: List[Dict[str, Any]] = []

    def add_entry(self, message: ChildToParentMessage) -> None:
        """
        Append a sanitized message to the ledger.

        Args:
            message (ChildToParentMessage): The message from a child agent.
        """
        sanitized_text = self._sanitize(message.payload.text)

        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "agent_id": message.agent_id,
            "round": message.round_number,
            "text": sanitized_text,
            "citations": [c.model_dump() for c in message.payload.citations]
        }
        self.entries.append(entry)

    def _sanitize(self, text: str) -> str:
        """
        6.2.3: Strip formatting anomalies and toxic string tokens.

        Args:
            text (str): Raw input text.

        Returns:
            str: Sanitized output.
        """
        # 1. Normalize whitespace (remove tabs, multiple spaces, etc.)
        text = " ".join(text.split())

        # 2. Strip non-printable or suspicious control characters
        text = re.sub(r"[^\x20-\x7E\n]", "", text)

        # 3. Simple protection against prompt injection "escape" patterns
        # (e.g., sequences often used to break out of system instructions)
        toxic_patterns = [r"\[/INST\]", r"\[INST\]", r"<<SYS>>", r"<</SYS>>"]
        for pattern in toxic_patterns:
            text = re.sub(pattern, "[REDACTED]", text, flags=re.IGNORECASE)

        return text.strip()

    def get_full_history_strings(self) -> List[str]:
        """
        Format the ledger into a list of display strings for the LLM.

        Returns:
            List[str]: Chronological list of 'AgentID: Content' strings.
        """
        return [f"{e['agent_id']}: {e['text']}" for e in self.entries]

    def to_list(self) -> List[Dict[str, Any]]:
        """
        Serialize the entire ledger for disk backup.

        Returns:
            List[Dict[str, Any]]: Raw list of entry dictionaries.
        """
        return self.entries

    def load_from_list(self, data: List[Dict[str, Any]]) -> None:
        """
        Restore ledger state from a serialized list.

        Args:
            data (List[Dict[str, Any]]): Serialized ledger entries.
        """
        self.entries = data
