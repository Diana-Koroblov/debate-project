"""Global logger initialization utility."""

from __future__ import annotations

import logging
from pathlib import Path

from debate_sdk.shared.config import load_logging_config
from debate_sdk.shared.logging_handler import FIFORotatingHandler


def setup_logger(name: str = "debate_project") -> logging.Logger:
    """
    Initialize and return a logger with the custom FIFO rotating handler.

    Args:
        name (str): Name of the logger to initialize.

    Returns:
        logging.Logger: The configured logger instance.
    """
    config = load_logging_config()
    logger = logging.getLogger(name)

    # Avoid duplicate handlers if setup_logger is called multiple times
    if logger.handlers:
        return logger

    logger.setLevel(config.get("log_level", "INFO"))

    log_dir = Path(config["log_directory"])
    if not log_dir.is_absolute():
        # Resolve relative to project root (parents[3] of config.py)
        # But here we can just resolve relative to current working directory
        # as the project usually runs from the root.
        pass

    handler = FIFORotatingHandler(
        log_dir=config["log_directory"],
        max_files=config["max_files"],
        max_lines=config["max_lines_per_file"],
        encoding="utf-8"
    )

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    handler.setFormatter(formatter)

    logger.addHandler(handler)
    return logger
