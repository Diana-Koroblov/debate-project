"""Mixin providing Google Gemini API integration to agents."""

from __future__ import annotations

import os
from typing import Any, Dict, List

import google.generativeai as genai
from pydantic import BaseModel

from debate_sdk.shared.gatekeeper import ApiGatekeeper
from debate_sdk.shared.logger import setup_logger

logger = setup_logger("gemini_mixin")


class GeminiMixin:
    """
    Encapsulates Google Gemini API orchestration.
    
    This mixin manages model instantiation, system prompts, 
    and structured output generation.
    """

    def __init__(
        self,
        model_name: str,
        system_instruction: str,
        generation_config: Dict[str, Any] = None
    ) -> None:
        """
        Initialize the Gemini model.

        Args:
            model_name (str): ID of the Gemini model (e.g., 'gemini-1.5-pro').
            system_instruction (str): The persona-defining system prompt.
            generation_config (Dict[str, Any]): Optional generation parameters.
        """
        api_key = os.getenv("GOOGLE_API_KEY", "")
        if not api_key:
            logger.error("GOOGLE_API_KEY not found in environment.")

        genai.configure(api_key=api_key)
        self._model = genai.GenerativeModel(
            model_name=model_name,
            system_instruction=system_instruction,
            generation_config=generation_config
        )
        self._chat = self._model.start_chat(history=[])
        # Initialize gatekeeper (Singleton)
        self._gatekeeper = ApiGatekeeper("config/rate_limits.json")

    def generate_argument(self, prompt: str) -> str:
        """
        Generate a text response from the model via ApiGatekeeper.

        Args:
            prompt (str): The user/orchestrator prompt.

        Returns:
            str: The generated response text.
        """
        try:
            # Wrap the API call in the gatekeeper
            response = self._gatekeeper.execute(
                self._chat.send_message,
                prompt,
                projected_cost_tokens=2000.0  # Conservative estimate
            )
            return response.text
        except Exception as exc:
            logger.error(f"Gemini generation failed: {exc}")
            # Reraise to let ParentJudgeAgent catch it (Sub-task 6.5.1)
            raise
