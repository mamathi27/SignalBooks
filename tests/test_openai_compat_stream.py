import json

import httpx
import pytest

from app.config import Settings
from app.services.llm import LLMStreamEvent
from app.services.openai_compat import OpenAICompatibleLLM
from app.services.retry import PermanentLLMError, TransientLLMError


@pytest.fixture
def settings():
    return Settings(
        llm_api_key="test-key",
        llm_model="test-model",
        price_input_per_million=0.15,
        price_output_per_million=0.60,
        usd_to_inr_rate=85.0,
    )


def test_stream_receives_chunks_and_final_usage(settings, monkeypatch):
    lines = [
        "data: " + json.dumps({
            "model": "test-model",
            "choices": [{"delta": {"content": "ARPU "}}],
        }),
        "data: " + json.dumps({
            "model": "test-model",
            "choices": [{"delta": {"content": "means average revenue per user."}}],
        }),
        "data: " + json.dumps({
            "model": "test-model",
            "choices": [],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 8,
            },
        }),
        "data: [DONE]",
    ]

    captured = {}

    class MockResponse:
        status_code = 200

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def iter_lines(self):
            return iter(lines)

    class MockClient:
        def __init__(self, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def stream(self, method, url, **kwargs):
            captured["method"] = method
            captured["url"] = url
            captured["payload"] = kwargs["json"]
            return MockResponse()

    monkeypatch.setattr(
        "app.services.openai_compat.httpx.Client",
        MockClient,
    )

    events = list(OpenAICompatibleLLM(settings).stream("What is ARPU?"))

    chunks = [
        event.text
        for event in events
        if isinstance(event, LLMStreamEvent) and event.text
    ]
    final = events[-1].final_response

    assert captured["method"] == "POST"
    assert captured["payload"]["stream"] is True
    assert captured["payload"]["stream_options"]["include_usage"] is True
    assert chunks == ["ARPU ", "means average revenue per user."]
    assert final.answer == "ARPU means average revenue per user."
    assert final.model == "test-model"
    assert final.input_tokens == 10
    assert final.output_tokens == 8
    assert final.usage_estimated is False
    assert final.cost_paise > 0


def test_stream_missing_api_key_fails_without_request(settings, monkeypatch):
    settings.llm_api_key = ""

    def unexpected_client(*args, **kwargs):
        pytest.fail("HTTP client should not be created without an API key")

    monkeypatch.setattr(
        "app.services.openai_compat.httpx.Client",
        unexpected_client,
    )

    with pytest.raises(PermanentLLMError, match="API key is not configured"):
        list(OpenAICompatibleLLM(settings).stream("What is ARPU?"))


def test_stream_timeout_is_transient(settings, monkeypatch):
    class MockClient:
        def __init__(self, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def stream(self, *args, **kwargs):
            raise httpx.TimeoutException("Streaming timed out")

    monkeypatch.setattr(
        "app.services.openai_compat.httpx.Client",
        MockClient,
    )

    with pytest.raises(TransientLLMError):
        list(OpenAICompatibleLLM(settings).stream("What is ARPU?"))


def test_stream_estimates_usage_when_provider_omits_it(settings, monkeypatch):
    lines = [
        "data: " + json.dumps({
            "choices": [{"delta": {"content": "A simulated answer."}}],
        }),
        "data: [DONE]",
    ]

    class MockResponse:
        status_code = 200

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def iter_lines(self):
            return iter(lines)

    class MockClient:
        def __init__(self, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def stream(self, *args, **kwargs):
            return MockResponse()

    monkeypatch.setattr(
        "app.services.openai_compat.httpx.Client",
        MockClient,
    )

    events = list(OpenAICompatibleLLM(settings).stream("What is ARPU?"))
    final = events[-1].final_response

    assert final.answer == "A simulated answer."
    assert final.usage_estimated is True
    assert final.input_tokens >= 1
    assert final.output_tokens >= 1
