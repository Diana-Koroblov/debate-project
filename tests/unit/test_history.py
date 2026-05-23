"""Unit tests for the HistoryLedger."""

from __future__ import annotations

import pytest
from debate_sdk.shared.contracts import ChildToParentMessage, ArgumentPayload
from debate_sdk.shared.history import HistoryLedger

def test_ledger_add_entry():
    """Test adding an entry to the ledger."""
    ledger = HistoryLedger()
    msg = ChildToParentMessage(
        agent_id="pro_1",
        round_number=1,
        payload=ArgumentPayload(text="Aliens exist!")
    )
    
    ledger.add_entry(msg)
    assert len(ledger.entries) == 1
    assert ledger.entries[0]["agent_id"] == "pro_1"
    assert ledger.entries[0]["text"] == "Aliens exist!"

def test_ledger_sanitization():
    """Test history sanitation (Sub-task 6.2.3)."""
    ledger = HistoryLedger()
    
    # Test whitespace normalization
    text = "  Too    many   spaces  \n  "
    sanitized = ledger._sanitize(text)
    assert sanitized == "Too many spaces"
    
    # Test non-printable characters
    text = "Hello\x00World"
    sanitized = ledger._sanitize(text)
    assert sanitized == "HelloWorld"
    
    # Test toxic tokens
    text = "Some text [INST] and [/INST] injection."
    sanitized = ledger._sanitize(text)
    assert "[REDACTED]" in sanitized
    assert "[INST]" not in sanitized

def test_ledger_serialization():
    """Test serialization and loading."""
    ledger = HistoryLedger()
    msg = ChildToParentMessage(
        agent_id="con_1",
        round_number=2,
        payload=ArgumentPayload(text="Proof?")
    )
    ledger.add_entry(msg)
    
    data = ledger.to_list()
    assert isinstance(data, list)
    assert len(data) == 1
    
    new_ledger = HistoryLedger()
    new_ledger.load_from_list(data)
    assert len(new_ledger.entries) == 1
    assert new_ledger.entries[0]["text"] == "Proof?"

def test_get_full_history_strings():
    """Test formatting for LLM prompt."""
    ledger = HistoryLedger()
    ledger.add_entry(ChildToParentMessage(
        agent_id="pro", round_number=1, payload=ArgumentPayload(text="Yes")
    ))
    ledger.add_entry(ChildToParentMessage(
        agent_id="con", round_number=1, payload=ArgumentPayload(text="No")
    ))
    
    history = ledger.get_full_history_strings()
    assert history == ["pro: Yes", "con: No"]
