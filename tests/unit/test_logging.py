"""Unit tests for logging infrastructure and FIFO rotation."""

from __future__ import annotations

import json
import logging
import shutil
from pathlib import Path

import pytest

from debate_sdk.shared.config import load_logging_config
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
    log_file = temp_log_dir / "agent_logs_01.log"
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
    handler = FIFORotatingHandler(temp_log_dir, max_files=5, max_lines=5)
    assert handler._current_file_index == 1
    assert handler._current_line_count == 2

    # Emit more lines to hit limit
    logger = logging.getLogger("test_resume")
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    logger.info("Line 3")
    logger.info("Line 4")
    logger.info("Line 5") # Hits limit

    assert handler._current_line_count == 5

    logger.info("Line 6") # Should rotate
    assert handler._current_file_index == 2
    assert handler._current_line_count == 1

    handler.close()
    logger.removeHandler(handler)


def test_handler_initialization_at_limit(temp_log_dir: Path):
    """Test initialization when the latest file is already at the limit."""
    file1 = temp_log_dir / "agent_logs_01.log"
    file1.write_text("L1\nL2\nL3\nL4\nL5\n")

    handler = FIFORotatingHandler(temp_log_dir, max_files=5, max_lines=5)
    # Should have rotated immediately
    assert handler._current_file_index == 2
    assert handler._current_line_count == 0
    handler.close()


def test_load_logging_config_valid(tmp_path: Path):
    """Test loading a valid logging configuration."""
    config_file = tmp_path / "logging_config.json"
    data = {
        "version": "1.00",
        "log_directory": "results/logs",
        "max_files": 20,
        "max_lines_per_file": 500
    }
    config_file.write_text(json.dumps(data))

    config = load_logging_config(config_file)
    assert config["max_files"] == 20
    assert config["max_lines_per_file"] == 500


def test_load_logging_config_invalid(tmp_path: Path):
    """Test loading an invalid logging configuration."""
    config_file = tmp_path / "logging_config.json"
    data = {"version": "1.00"}  # Missing fields
    config_file.write_text(json.dumps(data))

    with pytest.raises(ValueError, match="Missing required logging fields"):
        load_logging_config(config_file)


def test_fifo_rotation_logic(temp_log_dir: Path):
    """Test that the handler rotates and purges files correctly."""
    max_files = 3
    max_lines = 5
    handler = FIFORotatingHandler(temp_log_dir, max_files, max_lines)
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger = logging.getLogger("test_fifo")
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    # Emit 15 lines -> should create 3 files of 5 lines each
    for i in range(15):
        logger.info(f"Line {i+1}")

    log_files = sorted(temp_log_dir.glob("agent_logs_*.log"))
    assert len(log_files) == 3
    assert log_files[0].name == "agent_logs_01.log"
    assert log_files[2].name == "agent_logs_03.log"

    # Verify content of first file
    with open(log_files[0], "r") as f:
        lines = f.readlines()
        assert len(lines) == 5
        assert lines[0].strip() == "Line 1"

    # Emit 1 more line -> should trigger rotation and purge oldest (File 1)
    logger.info("Line 16")

    log_files = sorted(temp_log_dir.glob("agent_logs_*.log"))
    assert len(log_files) == 3
    # File 01 should now contain lines 6-10 (previously File 02)
    with open(log_files[0], "r") as f:
        lines = f.readlines()
        assert lines[0].strip() == "Line 6"

    # File 03 should now contain line 16
    with open(log_files[2], "r") as f:
        lines = f.readlines()
        assert len(lines) == 1
        assert lines[0].strip() == "Line 16"

    handler.close()
    logger.removeHandler(handler)


def test_10001_lines_rotation(temp_log_dir: Path):
    """Test that 10,001 lines create exactly 20 files of 500 lines."""
    max_files = 20
    max_lines = 500
    handler = FIFORotatingHandler(temp_log_dir, max_files, max_lines)
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger = logging.getLogger("test_large")
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    # Emit 10,001 lines
    for i in range(10001):
        logger.info(f"L{i}")

    log_files = sorted(temp_log_dir.glob("agent_logs_*.log"))
    assert len(log_files) == 20

    # File 01 should start from Line 1 (L1) -> No, L500.
    # Lines 0-499 -> File 01
    # ...
    # Lines 9500-9999 -> File 20
    # Line 10000 -> Rotates. File 01 (L0-499) deleted.
    # Files 02-20 become 01-19.
    # New File 20 gets L10000.

    with open(log_files[0], "r") as f:
        lines = f.readlines()
        assert lines[0].strip() == "L500"

    with open(log_files[-1], "r") as f:
        lines = f.readlines()
        assert len(lines) == 1
        assert lines[0].strip() == "L10000"

    handler.close()
    logger.removeHandler(handler)
