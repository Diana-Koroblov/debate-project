"""Unit tests for logging infrastructure and FIFO rotation."""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

import pytest

from debate_sdk.shared.logger import setup_logger
from debate_sdk.shared.logging_handler import FIFORotatingHandler


@pytest.fixture
def temp_log_dir(tmp_path: Path) -> Path:
    """Fixture to provide a temporary log directory."""
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    yield log_dir
    shutil.rmtree(log_dir)


def test_setup_logger(temp_log_dir: Path, monkeypatch):
    """Test the setup_logger utility."""
    # Mock load_logging_config to use our temp dir
    config = {
        "version": "1.00",
        "log_directory": str(temp_log_dir),
        "max_files": 5,
        "max_lines_per_file": 10,
        "log_level": "DEBUG"
    }
    monkeypatch.setattr("debate_sdk.shared.logger.load_logging_config", lambda: config)

    logger = setup_logger("test_setup")
    assert logger.name == "test_setup"
    assert len(logger.handlers) == 1
    assert isinstance(logger.handlers[0], FIFORotatingHandler)

    logger.info("Test message")
    log_file = temp_log_dir / "test_setup_logs_01.log"
    assert log_file.exists()

    # Clean up to avoid PermissionError on Windows
    for handler in logger.handlers:
        handler.close()
    logger.handlers.clear()


def test_setup_logger_duplicate(temp_log_dir: Path, monkeypatch):
    """Test that setup_logger doesn't add duplicate handlers."""
    config = {
        "version": "1.00",
        "log_directory": str(temp_log_dir),
        "max_files": 5,
        "max_lines_per_file": 10,
        "log_level": "DEBUG"
    }
    monkeypatch.setattr("debate_sdk.shared.logger.load_logging_config", lambda: config)

    logger = setup_logger("test_duplicate")
    handler_count = len(logger.handlers)

    # Call again
    setup_logger("test_duplicate")
    assert len(logger.handlers) == handler_count

    for handler in logger.handlers:
        handler.close()
    logger.handlers.clear()


def test_handler_emit_error(temp_log_dir: Path):
    """Test error handling in emit."""
    handler = FIFORotatingHandler(temp_log_dir, max_files=5, max_lines=5)

    # Force an error by closing the stream manually
    handler._stream.close()

    # This should trigger handleError but not crash
    record = logging.LogRecord("test", logging.INFO, "path", 10, "msg", None, None)
    handler.emit(record)
    handler.close()


def test_handler_initialization_from_existing(temp_log_dir: Path):
    """Test that the handler correctly resumes from existing log files."""
    # Pre-create some log files
    file1 = temp_log_dir / "agent_logs_01.log"
    file1.write_text("Line 1\nLine 2\n")

    # Initialize handler
    handler = FIFORotatingHandler(temp_log_dir, max_files=5, max_lines=5, process_name="agent")
    assert handler._current_file_index == 1
    assert handler._current_line_count == 2

    # Emit more lines to hit limit
    logger = logging.getLogger("test_resume")
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    logger.info("Line 3")
    logger.info("Line 4")
    logger.info("Line 5")  # Hits limit

    assert handler._current_line_count == 5

    logger.info("Line 6")  # Should rotate
    assert handler._current_file_index == 2
    assert handler._current_line_count == 1

    handler.close()
    logger.removeHandler(handler)


def test_handler_initialization_at_limit(temp_log_dir: Path):
    """Test initialization when the latest file is already at the limit."""
    file1 = temp_log_dir / "agent_logs_01.log"
    file1.write_text("L1\nL2\nL3\nL4\nL5\n")

    handler = FIFORotatingHandler(temp_log_dir, max_files=5, max_lines=5, process_name="agent")
    # Should have rotated immediately
    assert handler._current_file_index == 2
    assert handler._current_line_count == 0
    handler.close()
