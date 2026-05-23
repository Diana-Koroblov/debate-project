"""Abstract Base Class for all multi-process debate agents.

This module establishes the core architectural contract for agents in the
debate swarm. It manages the agent's identity, its lifecycle state, and
the OS-level IPC primitives (Queues) required for decoupled communication.
By centralizing these primitives here, we ensure consistent behavior and
message routing across all concrete debater and judge instances.
"""

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
    """
    Abstract base class defining the core lifecycle and interface for debate agents.

    This class follows the single-responsibility principle, managing agent
    identification, runtime state tracking, and IPC communication while
    delegating message handling to concrete implementations.

    Attributes:
        agent_id (str): Unique identifier for the agent instance.
        config (Dict[str, Any]): Validated configuration dictionary.
        inbound_queue (Queue): OS-level channel for receiving messages.
        outbound_queue (Queue): OS-level channel for sending messages.
        is_running (bool): Flag indicating if the agent's loop is active.
        logger (logging.Logger): Logger instance specific to the agent's identity.
    """

    def __init__(
        self,
        agent_id: str,
        config: Dict[str, Any],
        inbound_queue: Queue,
        outbound_queue: Queue
    ) -> None:
        """
        Initialize the base agent state and communication channels.

        Args:
            agent_id (str): Unique identifier for the agent.
            config (Dict[str, Any]): Global setup configuration.
            inbound_queue (Queue): Input channel for this agent.
            outbound_queue (Queue): Output channel to the orchestrator.
        """
        self.agent_id = agent_id
        self.config = config
        self.inbound_queue = inbound_queue
        self.outbound_queue = outbound_queue
        self.is_running = False
        self.logger = setup_logger(f"agent.{agent_id}")
        self.logger.info(f"Initialized BaseAgent for '{agent_id}'")

    @abstractmethod
    def handle_message(self, message: AnyMessage) -> None:
        """
        Execute agent-specific logic upon receiving a validated message.

        Args:
            message (AnyMessage): The validated Pydantic message model.
        """
        raise NotImplementedError("Subclasses must implement handle_message")

    def _validate_payload(self, raw_message: Any) -> AnyMessage | None:
        """
        Centralized parser to validate and deserialize IPC payloads.

        Args:
            raw_message (Any): Raw string or dict from the OS pipeline.

        Returns:
            AnyMessage | None: Validated model or None if validation fails.
        """
        try:
            if isinstance(raw_message, str):
                return MESSAGE_ADAPTER.validate_json(raw_message)
            return MESSAGE_ADAPTER.validate_python(raw_message)
        except (json.JSONDecodeError, ValidationError) as exc:
            self.logger.error(f"DROPPED MALICIOUS PACKET: {exc}")
            return None

    def run(self) -> None:
        """
        Master entry-point function for the agent process event loop.
        """
        self.is_running = True
        self.logger.info(f"Event loop started for agent '{self.agent_id}'")

        # 3.3.1: Start background heartbeat thread
        hb_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        hb_thread.start()

        while self.is_running:
            try:
                # Blocking extraction with timeout for CPU efficiency
                raw_data = self.inbound_queue.get(timeout=1.0)
                message = self._validate_payload(raw_data)
                if message:
                    self.handle_message(message)
            except queue.Empty:
                # Normal timeout, continue polling
                continue
            except BudgetExceededException:
                # 6.5.1: Propagate budget exhaustion to orchestrator
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
        """Background loop for health telemetry (Sub-task 3.3.1)."""
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
        """
        Standardized hook to emit token telemetry for the Token Economy.

        This method instantiates a structured telemetry message and routes
        it to the outbound OS pipeline for centralized tracking.

        Args:
            input_tokens (int): Count of tokens sent to the LLM.
            output_tokens (int): Count of tokens received from the LLM.
            latency_ms (float): Response time in milliseconds.
            model (str): Name of the model used.
        """
        telemetry = {
            "type": "telemetry",
            "agent_id": self.agent_id,
            "model": model,
            "usage": {"input": input_tokens, "output": output_tokens},
            "latency_ms": latency_ms,
            "timestamp": datetime.utcnow().isoformat()
        }
        self.send_message(telemetry)

    def send_message(self, message: Dict[str, Any]) -> None:
        """
        Dispatch a structured payload to the outbound OS pipeline.

        This method encapsulates the non-blocking push to the outbound
        queue, ensuring consistent logging of all agent output.

        Args:
            message (Dict[str, Any]): The JSON-serializable dictionary to send.
        """
        self.logger.debug(f"Sending message: {message}")
        try:
            self.outbound_queue.put_nowait(message)
        except Exception as exc:
            self.logger.error(f"Failed to push message to OS pipeline: {exc}")
