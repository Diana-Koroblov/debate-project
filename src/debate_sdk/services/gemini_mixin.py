"""Compatibility shim for the legacy Gemini mixin import path."""

from debate_sdk.services.groq_mixin import GroqMixin as GeminiMixin

__all__ = ["GeminiMixin"]
