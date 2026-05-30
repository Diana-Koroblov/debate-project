from unittest.mock import MagicMock, patch

import httpx
import pytest

from debate_sdk.services.groq_mixin import DEFAULT_BASE_URL, GroqMixin, _format_http_error


class _GroqHarness(GroqMixin):
    def __init__(self) -> None:
        self.agent_id = "agent-1"
        self.outbound_queue = None

    def configure(self, model_name: str, system_instruction: str, generation_config=None) -> None:
        GroqMixin.__init__(self, model_name, system_instruction, generation_config)


def test_format_http_error_prefers_response_text_and_handles_text_failures():
    request = httpx.Request("POST", "https://example.com")
    response = httpx.Response(429, request=request, text="retry later")
    exc = httpx.HTTPStatusError("boom", request=request, response=response)
    assert _format_http_error(exc) == "HTTP 429: retry later"

    class BrokenResponse:
        status_code = 500

        @property
        def text(self) -> str:
            raise RuntimeError("no text")

    class BrokenError:
        response = BrokenResponse()

        def __str__(self) -> str:
            return "broken"

    assert _format_http_error(BrokenError()) == "HTTP 500: broken"


def test_groq_init_logs_missing_api_key_and_uses_transport_defaults(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    with (
        patch("debate_sdk.services.groq_mixin.logger.exception") as log_exception,
        patch("debate_sdk.services.groq_mixin.httpx.Client") as client_cls,
        patch("debate_sdk.services.groq_mixin.ApiGatekeeper") as gatekeeper_cls,
    ):
        harness = _GroqHarness()
        harness.configure("model-x", "system")

    log_exception.assert_called_once()
    client_cls.assert_called_once()
    assert client_cls.call_args.kwargs["base_url"] == DEFAULT_BASE_URL
    assert client_cls.call_args.kwargs["timeout"] == 60.0
    gatekeeper_cls.assert_called_once()
    assert harness._model is harness._client


def test_send_chat_completion_builds_json_payload_and_returns_usage(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "token")
    response = MagicMock()
    response.raise_for_status.return_value = None
    response.json.return_value = {
        "choices": [{"message": {"content": "answer"}}],
        "usage": {"prompt_tokens": 11, "completion_tokens": 7},
    }
    client = MagicMock(post=MagicMock(return_value=response))

    with (
        patch("debate_sdk.services.groq_mixin.httpx.Client", return_value=client),
        patch("debate_sdk.services.groq_mixin.ApiGatekeeper"),
    ):
        harness = _GroqHarness()
        harness.configure(
            "model-y",
            "system",
            {"response_mime_type": "application/json", "max_completion_tokens": 12},
        )
        result = harness._send_chat_completion("prompt")

    payload = client.post.call_args.kwargs["json"]
    assert payload["response_format"] == {"type": "json_object"}
    assert payload["max_completion_tokens"] == 12
    assert result == {"text": "answer", "input_tokens": 11, "output_tokens": 7}


def test_send_chat_completion_raises_for_http_failures_and_missing_message_content(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "token")
    request = httpx.Request("POST", "https://example.com")
    bad_response = httpx.Response(400, request=request, text="bad request")
    missing_content_response = MagicMock()
    missing_content_response.raise_for_status.return_value = None
    missing_content_response.json.return_value = {"choices": [{}]}

    with (
        patch("debate_sdk.services.groq_mixin.ApiGatekeeper"),
        patch("debate_sdk.services.groq_mixin.httpx.Client") as client_cls,
    ):
        http_client = client_cls.return_value
        harness = _GroqHarness()
        harness.configure("model-z", "system")

        http_client.post.return_value = MagicMock(
            raise_for_status=MagicMock(
                side_effect=httpx.HTTPStatusError("boom", request=request, response=bad_response)
            )
        )
        with pytest.raises(RuntimeError, match="HTTP 400: bad request"):
            harness._send_chat_completion("prompt")

        http_client.post.return_value = missing_content_response
        with pytest.raises(RuntimeError, match="did not include message content"):
            harness._send_chat_completion("prompt")


def test_generate_argument_logs_and_reraises_gatekeeper_failures(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "token")
    gatekeeper = MagicMock()
    gatekeeper.execute.side_effect = RuntimeError("network down")

    with (
        patch("debate_sdk.services.groq_mixin.httpx.Client"),
        patch("debate_sdk.services.groq_mixin.ApiGatekeeper", return_value=gatekeeper),
        patch("debate_sdk.services.groq_mixin.logger.error") as log_error,
    ):
        harness = _GroqHarness()
        harness.configure("model-a", "system")
        with pytest.raises(RuntimeError, match="network down"):
            harness.generate_argument("prompt")

    log_error.assert_called_once()