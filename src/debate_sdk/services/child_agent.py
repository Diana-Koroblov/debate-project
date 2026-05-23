"""Intermediate abstraction for debater agents with search capabilities."""

from __future__ import annotations

import json
from multiprocessing import Queue
from typing import Any, Dict, List

from debate_sdk.services.base_agent import BaseAgent
from debate_sdk.services.web_search_mixin import WebSearchMixin
from debate_sdk.shared.contracts import (
    ArgumentPayload,
    ChildToParentMessage,
    MessageType,
    ParentToChildRouter,
)


class ChildDebaterAgent(BaseAgent, WebSearchMixin):
    """
    Intermediate base class for Pro and Con debater agents.
    """

    def __init__(
        self,
        agent_id: str,
        config: Dict[str, Any],
        inbound_queue: Queue,
        outbound_queue: Queue
    ) -> None:
        """Initialize the debater agent with search mixin."""
        super().__init__(agent_id, config, inbound_queue, outbound_queue)
        WebSearchMixin.__init__(self)

    def handle_message(self, message: Any) -> None:
        """Process an incoming IPC message."""
        if not isinstance(message, ParentToChildRouter):
            return

        if message.type == MessageType.TURN_PROMPT:
            self._execute_turn(message)

    def _execute_turn(self, prompt: ParentToChildRouter) -> None:
        """
        Execute a debate turn: generate, parse, and emit.
        """
        self.logger.info(f"Agent '{self.agent_id}' generating argument...")
        
        # Subclasses must provide generate_argument (usually via GeminiMixin)
        user_prompt = f"OPPONENT HISTORY:\n{prompt.history}\n\nGenerate your structured response."
        raw_output = getattr(self, "generate_argument")(user_prompt)
        
        try:
            data = json.loads(raw_output)
            argument_text = data.get("text")
            if not argument_text:
                self.logger.warning("Empty text in agent response. Dropping.")
                return

            citations = data.get("citations", [])
            
            # Emission
            self.emit_argument(
                text=argument_text,
                round_num=len(prompt.history) // 2 + 1,
                citations=citations
            )
        except json.JSONDecodeError:
            self.logger.error("RUNTIME SCHEMA VIOLATION: Dropping malformed emission.")
            # 5.6.5: Dropped without bringing down the process

    def emit_argument(self, text: str, round_num: int, citations: List[Any] = None) -> None:
        """
        Construct and send a validated argument message to the orchestrator.

        Args:
            text (str): The generated argument text.
            round_num (int): Current debate round.
            citations (List[Citation]): Supporting evidence.
        """
        payload = ArgumentPayload(
            text=text,
            citations=citations or []
        )

        message = ChildToParentMessage(
            agent_id=self.agent_id,
            round_number=round_num,
            payload=payload
        )

        self.send_message(message.model_dump())
        self.logger.info(f"Argument emitted for round {round_num}")
