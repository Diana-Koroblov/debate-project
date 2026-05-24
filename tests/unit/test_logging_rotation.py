"""Rotation and config loading tests for logging infrastructure."""

from __future__ import annotations

import json
import logging
import shutil
from pathlib import Path

import pytest

from debate_sdk.shared.config import load_logging_config
from debate_sdk.shared.logging_handler import FIFORotatingHandler


@pytest.fixture
def temp_log_dir(tmp_path: Path) -> Path:
    """Fixture to provide a temporary log directory."""
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    yield log_dir
    shutil.rmtree(log_dir)


def test_load_logging_config_valid(tmp_path: Path):
    """Test loading a valid logging configuration."""
    config_file = tmp_path / "logging_config.json"
    data = {
        "version": "1.00",
        "log_directory": "results/logs",
        "max_files": 20,
        "max_lines_per_file": 500,
    }
    config_file.write_text(json.dumps(data))

    config = load_logging_config(config_file)
    assert config["max_files"] == 20
    assert config["max_lines_per_file"] == 500


def test_load_logging_config_invalid(tmp_path: Path):
    """Test loading an invalid logging configuration."""
    config_file = tmp_path / "logging_config.json"
    config_file.write_text(json.dumps({"version": "1.00"}))

    with pytest.raises(ValueError, match="Missing required logging fields"):
        load_logging_config(config_file)


def test_fifo_rotation_logic(temp_log_dir: Path):
    """Test that the handler rotates and purges files correctly."""
    handler = FIFORotatingHandler(temp_log_dir, max_files=3, max_lines=5)
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger = logging.getLogger("test_fifo")
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    for i in range(15):
        logger.info(f"Line {i + 1}")

    log_files = sorted(temp_log_dir.glob("agent_logs_*.log"))
    assert len(log_files) == 3
    assert log_files[0].name == "agent_logs_01.log"
    assert log_files[2].name == "agent_logs_03.log"

    with open(log_files[0], "r", encoding="utf-8") as stream:
        lines = stream.readlines()
        assert len(lines) == 5
        assert lines[0].strip() == "Line 1"

    logger.info("Line 16")

    log_files = sorted(temp_log_dir.glob("agent_logs_*.log"))
    assert len(log_files) == 3
    with open(log_files[0], "r", encoding="utf-8") as stream:
        lines = stream.readlines()
        assert lines[0].strip() == "Line 6"

    with open(log_files[2], "r", encoding="utf-8") as stream:
        lines = stream.readlines()
        assert len(lines) == 1
        assert lines[0].strip() == "Line 16"

    handler.close()
    logger.removeHandler(handler)


def test_10001_lines_rotation(temp_log_dir: Path):
    """Test that 10,001 lines create exactly 20 files of 500 lines."""
    handler = FIFORotatingHandler(temp_log_dir, max_files=20, max_lines=500)
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger = logging.getLogger("test_large")
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    for i in range(10001):
        logger.info(f"L{i}")

    log_files = sorted(temp_log_dir.glob("agent_logs_*.log"))
    assert len(log_files) == 20

    with open(log_files[0], "r", encoding="utf-8") as stream:
        lines = stream.readlines()
        assert lines[0].strip() == "L500"

    with open(log_files[-1], "r", encoding="utf-8") as stream:
        lines = stream.readlines()
        assert len(lines) == 1
        assert lines[0].strip() == "L10000"

    handler.close()
    logger.removeHandler(handler)
