"""Utility functions for OS-level process management and termination."""

from __future__ import annotations

import psutil

from debate_sdk.shared.logger import setup_logger

logger = setup_logger("process_utils")


def terminate_process_tree(pid: int, timeout: float = 3.0) -> bool:
    """
    Forcibly terminate a process and all its children.

    Args:
        pid (int): OS Process ID of the root process to kill.
        timeout (float): Seconds to wait for graceful termination before SIGKILL.

    Returns:
        bool: True if the process and its children were successfully terminated.
    """
    try:
        parent = psutil.Process(pid)
    except psutil.NoSuchProcess:
        logger.warning(f"Process PID {pid} not found for termination.")
        return True

    children = parent.children(recursive=True)
    logger.info(f"Terminating process tree for PID {pid} ({len(children)} children).")

    # Attempt SIGTERM first for graceful exit
    for child in children:
        child.terminate()
    parent.terminate()

    # Wait for processes to terminate
    gone, alive = psutil.wait_procs(children + [parent], timeout=timeout)

    # Forcibly kill any remaining processes
    for process in alive:
        logger.warning(f"Process {process.pid} refused to terminate. Sending SIGKILL.")
        process.kill()

    # Final check
    _, still_alive = psutil.wait_procs(alive, timeout=1.0)
    if still_alive:
        logger.error(f"Failed to kill some processes: {[p.pid for p in still_alive]}")
        return False

    return True


def is_process_alive(pid: int) -> bool:
    """Check if a process with a given PID is still running."""
    try:
        return psutil.Process(pid).is_running()
    except psutil.NoSuchProcess:
        return False
