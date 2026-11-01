import httpx
import pytest

from app.config import Settings
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


def test_success_with_provider_usage(settings, monkeypatch):
    class MockResponse:
        status_code = 200

        def json(self):
            return {
                "model": "test-model",
                "choices": [
                    {"message": {"content": "ARPU means average revenue per user."}}
                ],
                "usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 8,
                },
            }

    class MockClient:
        def __init__(self, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def post(self, *args, **kwargs):
            return MockResponse()

    monkeypatch.setattr("app.services.openai_compat.httpx.Client", MockClient)

    result = OpenAICompatibleLLM(settings).generate("What is ARPU?")

    assert result.answer == "ARPU means average revenue per user."
    assert result.model == "test-model"
    assert result.input_tokens == 10
    assert result.output_tokens == 8
    assert result.usage_estimated is False
    assert result.cost_paise > 0


def test_missing_provider_usage_is_estimated(settings, monkeypatch):
    class MockResponse:
        status_code = 200

        def json(self):
            return {
                "model": "test-model",
                "choices": [
                    {"message": {"content": "A simulated answer."}}
                ],
            }

    class MockClient:
        def __init__(self, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def post(self, *args, **kwargs):
            return MockResponse()

    monkeypatch.setattr("app.services.openai_compat.httpx.Client", MockClient)

    result = OpenAICompatibleLLM(settings).generate("What is ARPU?")

    assert result.usage_estimated is True
    assert result.input_tokens >= 1
    assert result.output_tokens >= 1


def test_missing_api_key_fails_without_request(settings, monkeypatch):
    settings.llm_api_key = ""

    def unexpected_client(*args, **kwargs):
        pytest.fail("HTTP client should not be created without an API key")

    monkeypatch.setattr("app.services.openai_compat.httpx.Client", unexpected_client)

    with pytest.raises(PermanentLLMError, match="API key is not configured"):
        OpenAICompatibleLLM(settings).generate("What is ARPU?")


def test_timeout_is_transient(settings, monkeypatch):
    class MockClient:
        def __init__(self, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def post(self, *args, **kwargs):
            raise httpx.TimeoutException("Request timed out")

    monkeypatch.setattr("app.services.openai_compat.httpx.Client", MockClient)

    with pytest.raises(TransientLLMError):
        OpenAICompatibleLLM(settings).generate("What is ARPU?")


@pytest.mark.parametrize("status_code", [400, 401, 403, 404])
def test_permanent_http_errors_are_not_retryable(
    settings, monkeypatch, status_code
):
    class MockResponse:
        def __init__(self):
            self.status_code = status_code

    class MockClient:
        def __init__(self, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def post(self, *args, **kwargs):
            return MockResponse()

    monkeypatch.setattr("app.services.openai_compat.httpx.Client", MockClient)

    with pytest.raises(PermanentLLMError):
        OpenAICompatibleLLM(settings).generate("What is ARPU?")


@pytest.mark.parametrize("status_code", [429, 500, 502, 503, 504])
def test_temporary_http_errors_are_retryable(
    settings, monkeypatch, status_code
):
    class MockResponse:
        def __init__(self):
            self.status_code = status_code

    class MockClient:
        def __init__(self, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def post(self, *args, **kwargs):
            return MockResponse()

    monkeypatch.setattr("app.services.openai_compat.httpx.Client", MockClient)

    with pytest.raises(TransientLLMError):
        OpenAICompatibleLLM(settings).generate("What is ARPU?")
