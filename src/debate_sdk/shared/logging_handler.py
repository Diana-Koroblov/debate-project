"""Custom logging handler for line-based FIFO rotation."""

from __future__ import annotations

import logging
from pathlib import Path


class FIFORotatingHandler(logging.Handler):
    """
    Handler that rotates logs based on line count and maintains a FIFO buffer.

    Attributes:
        log_dir (Path): Directory where log files are stored.
        max_files (int): Maximum number of log files to maintain.
        max_lines (int): Maximum number of lines allowed per file.
    """

    def __init__(
        self,
        log_dir: str | Path,
        max_files: int,
        max_lines: int,
        encoding: str = "utf-8",
        process_name: str = "agent"
    ) -> None:
        super().__init__()
        self.log_dir = Path(log_dir)
        self.max_files = max_files
        self.max_lines = max_lines
        self.encoding = encoding
        self.process_name = process_name
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self._current_file_index = 0
        self._current_line_count = 0
        self._stream = None
        self._initialize_state()

    def _initialize_state(self) -> None:
        """Find the latest log file and its line count."""
        existing_logs = sorted(self.log_dir.glob(f"{self.process_name}_logs_*.log"))
        if not existing_logs:
            self._rotate()
            return

        latest_file = existing_logs[-1]
        try:
            index_str = latest_file.stem.split("_")[-1]
            self._current_file_index = int(index_str)
        except (ValueError, IndexError):
            self._current_file_index = 1

        with open(latest_file, "r", encoding=self.encoding) as f:
            self._current_line_count = sum(1 for _ in f)

        if self._current_line_count >= self.max_lines:
            self._rotate()
        else:
            self._stream = open(latest_file, "a", encoding=self.encoding)  # noqa: SIM115
            self._current_line_count = self._current_line_count # Ensure sync

    def _rotate(self) -> None:
        """Rotate to a new log file, purging the oldest if at max_files."""
        if self._stream:
            self._stream.close()

        self._current_file_index += 1
        if self._current_file_index > self.max_files:
            # Shift all files down (FIFO)
            self._purge_and_shift()
            self._current_file_index = self.max_files

        new_file = self.log_dir / f"{self.process_name}_logs_{self._current_file_index:02d}.log"
        self._stream = open(new_file, "w", encoding=self.encoding)  # noqa: SIM115
        self._current_line_count = 0

    def _purge_and_shift(self) -> None:
        """Purge the oldest file and shift indices of existing ones."""
        oldest = self.log_dir / f"{self.process_name}_logs_01.log"
        if oldest.exists():
            oldest.unlink()

        for i in range(2, self.max_files + 1):
            src = self.log_dir / f"{self.process_name}_logs_{i:02d}.log"
            if src.exists():
                dst = self.log_dir / f"{self.process_name}_logs_{i-1:02d}.log"
                src.rename(dst)

    def _write_line(self, line: str) -> None:
        """Write one physical line, rotating first when the file is full."""
        if self._current_line_count >= self.max_lines:
            self._rotate()

        if not self._stream:
            return

        self._stream.write(line + "\n")
        self._stream.flush()
        self._current_line_count += 1

    def emit(self, record: logging.LogRecord) -> None:
        """Emit a record, rotating if necessary."""
        try:
            msg = self.format(record)
            for line in msg.splitlines() or [""]:
                self._write_line(line)
        except Exception:
            self.handleError(record)

    def close(self) -> None:
        """Close the current stream."""
        if self._stream:
            self._stream.close()
            self._stream = None
        super().close()
