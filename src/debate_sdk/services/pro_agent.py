"""Pro-Stance Debater Agent realization."""

from __future__ import annotations

from multiprocessing import Queue
from typing import Any, Dict

from debate_sdk.services.child_agent import ChildDebaterAgent
from debate_sdk.services.groq_mixin import GroqMixin


class ProDebaterAgent(ChildDebaterAgent, GroqMixin):
    """
    Agent specialized in arguing for the existence of extraterrestrial life.

    This agent utilizes the Groq API to generate evidence-based arguments
    and the Search tool to gather real-time astrophysical data.
    """

    def __init__(
        self,
        agent_id: str,
        config: Dict[str, Any],
        inbound_queue: Queue,
        outbound_queue: Queue
    ) -> None:
        """Initialize the pro agent with persona and Groq model."""
        super().__init__(agent_id, config, inbound_queue, outbound_queue)

        # Load model name and persona from setup config
        debate_cfg = config.get("debate", {})
        model_name = debate_cfg.get("model", "openai/gpt-oss-20b")

        # Build comprehensive system instruction (Sub-task 5.5)
        base_persona = debate_cfg.get("pro_persona", "You are a pro-alien scientist.")
        rules = "\n".join(debate_cfg.get("adversarial_rules", []))
        fmt = debate_cfg.get("formatting_instructions", "")
        role_instruction = "You are the pro debater. You must argue in favor of the topic."
        system_prompt = (
            f"{role_instruction}\n{base_persona}\n\nDEBATE PROTOCOLS:\n{rules}\n\n{fmt}"
        )

        GroqMixin.__init__(
            self,
            model_name=model_name,
            system_instruction=system_prompt,
            generation_config={
                "response_mime_type": "application/json",
                "max_completion_tokens": 256,
            }
        )
