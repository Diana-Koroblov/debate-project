"""Mixin providing Groq API integration to debate agents."""

from __future__ import annotations

import os
from typing import Any, Dict

import httpx
from dotenv import load_dotenv

from debate_sdk.shared.gatekeeper import ApiGatekeeper
from debate_sdk.shared.logger import setup_logger

load_dotenv()
logger = setup_logger("groq_mixin")

DEFAULT_BASE_URL = "https://api.groq.com/openai/v1"


def _format_http_error(exc: httpx.HTTPStatusError) -> str:
    response = exc.response
    try:
        detail = response.text.strip()
    except Exception:
        detail = ""
    if detail:
        return f"HTTP {response.status_code}: {detail}"
    return f"HTTP {response.status_code}: {exc}"


class GroqMixin:
    """Encapsulates Groq chat-completions orchestration."""

    def __init__(
        self,
        model_name: str,
        system_instruction: str,
        generation_config: Dict[str, Any] = None,
    ) -> None:
        """Initialize the Groq client and gatekeeper plumbing."""
        api_key = os.getenv("GROQ_API_KEY", "")
        if not api_key:
            try:
                raise EnvironmentError(
                    "No API key inputted in the settings. "
                    "Please set GROQ_API_KEY."
                )
            except EnvironmentError:
                logger.exception("API key configuration exception")

        self._model_name = model_name
        self._system_instruction = system_instruction
        self._generation_config = generation_config or {}
        self._client = httpx.Client(
            base_url=os.getenv("GROQ_BASE_URL", DEFAULT_BASE_URL),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            timeout=float(os.getenv("GROQ_TIMEOUT_SECONDS", "60")),
        )
        # Preserve the legacy attribute name used by some tests.
        self._model = self._client
        self._gatekeeper = ApiGatekeeper(
            "config/rate_limits.json",
            agent_id=getattr(self, "agent_id", "unknown"),
            model_name=model_name,
            outbound_queue=getattr(self, "outbound_queue", None),
        )

    def _send_chat_completion(self, prompt: str) -> dict[str, Any]:
        """Execute one Groq chat-completions request and normalize the response."""
        payload = {
            "model": self._model_name,
            "messages": [
                {"role": "system", "content": self._system_instruction},
                {"role": "user", "content": prompt},
            ],
            "temperature": max(float(self._generation_config.get("temperature", 0.2)), 1e-8),
        }
        max_completion_tokens = self._generation_config.get("max_completion_tokens")
        if max_completion_tokens is not None:
            payload["max_completion_tokens"] = int(max_completion_tokens)
        if self._generation_config.get("response_mime_type") == "application/json":
            payload["response_format"] = {"type": "json_object"}
        response = self._client.post("/chat/completions", json=payload)
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise RuntimeError(_format_http_error(exc)) from None
        data = response.json()

        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError("Groq response did not include message content") from exc

        usage = data.get("usage", {})
        return {
            "text": content,
            "input_tokens": int(usage.get("prompt_tokens", 0)),
            "output_tokens": int(usage.get("completion_tokens", 0)),
        }

    def generate_argument(self, prompt: str) -> str:
        """Generate a text response from Groq via ApiGatekeeper."""
        try:
            result = self._gatekeeper.execute(
                self._send_chat_completion,
                prompt,
                projected_cost_tokens=2000.0,
            )
            return str(result["text"])
        except Exception as exc:
            logger.error("Groq generation failed: %s", exc)
            raise