from debate_sdk.services.gemini_mixin import GeminiMixin, __all__
from debate_sdk.services.groq_mixin import GroqMixin


def test_gemini_mixin_aliases_groq_mixin():
    assert GeminiMixin is GroqMixin
    assert __all__ == ["GeminiMixin"]