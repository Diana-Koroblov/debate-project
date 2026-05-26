"""Base class for debate agents communicating over multiprocessing queues."""

from __future__ import annotations

import json
import queue
import threading
import time
from abc import ABC, abstractmethod
from datetime import datetime
from multiprocessing import Queue
from typing import Any, Dict

from pydantic import ValidationError

from debate_sdk.shared.contracts import MESSAGE_ADAPTER, AnyMessage
from debate_sdk.shared.exceptions import BudgetExceededException
from debate_sdk.shared.logger import setup_logger


class BaseAgent(ABC):
    """Core lifecycle and IPC contract for concrete debate agents."""

    def __init__(
        self,
        agent_id: str,
        config: Dict[str, Any],
        inbound_queue: Queue,
        outbound_queue: Queue
    ) -> None:
        self.agent_id = agent_id
        self.config = config
        self.inbound_queue = inbound_queue
        self.outbound_queue = outbound_queue
        self.is_running = False
        self.logger = setup_logger(f"agent.{agent_id}")
        self.logger.info(f"Initialized BaseAgent for '{agent_id}'")

    @abstractmethod
    def handle_message(self, message: AnyMessage) -> None:
        """Execute agent-specific logic for one validated message."""
        raise NotImplementedError("Subclasses must implement handle_message")

    def _validate_payload(self, raw_message: Any) -> AnyMessage | None:
        """Validate and deserialize IPC payloads."""
        try:
            if isinstance(raw_message, str):
                return MESSAGE_ADAPTER.validate_json(raw_message)
            return MESSAGE_ADAPTER.validate_python(raw_message)
        except (json.JSONDecodeError, ValidationError) as exc:
            self.logger.error(f"DROPPED MALICIOUS PACKET: {exc}")
            return None

    def run(self) -> None:
        """Start the agent event loop."""
        self.is_running = True
        self.logger.info(f"Event loop started for agent '{self.agent_id}'")
        hb_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        hb_thread.start()
        while self.is_running:
            try:
                raw_data = self.inbound_queue.get(timeout=1.0)
                message = self._validate_payload(raw_data)
                if message:
                    self.handle_message(message)
            except queue.Empty:
                continue
            except BudgetExceededException:
                raise
            except Exception as exc:
                self.logger.error(f"Critical error in agent event loop: {exc}")
                self.terminate()
        self.logger.info(f"Event loop terminated for agent '{self.agent_id}'")

    def terminate(self) -> None:
        """Gracefully signal the agent to cease operations."""
        self.is_running = False
        self.logger.info(f"Termination signal received for agent '{self.agent_id}'")

    def _heartbeat_loop(self) -> None:
        """Background loop for health telemetry."""
        hb_interval = self.config.get("watchdog", {}).get("check_interval_seconds", 2)
        while self.is_running:
            heartbeat = {
                "type": "heartbeat",
                "agent_id": self.agent_id,
                "timestamp": datetime.utcnow().isoformat()
            }
            self.send_message(heartbeat)
            time.sleep(hb_interval)

    def log_token_usage(
        self,
        input_tokens: int,
        output_tokens: int,
        latency_ms: float,
        model: str = "unknown"
    ) -> None:
        """Emit token telemetry to the outbound queue."""
        telemetry = {
            "type": "telemetry",
            "agent_id": self.agent_id,
            "model": model,
            "usage": {"input": input_tokens, "output": output_tokens},
            "latency_ms": float(latency_ms),
            "timestamp": float(time.time())
        }
        self.send_message(telemetry)

    def send_message(self, message: Dict[str, Any]) -> None:
        """Dispatch a structured payload to the outbound OS pipeline."""
        self.logger.debug(f"Sending message: {message}")
        try:
            self.outbound_queue.put_nowait(message)
        except Exception as exc:
            self.logger.error(f"Failed to push message to OS pipeline: {exc}")
