
import pytest

from app.services.llm import (
    FakeLLM,
    FallbackLLM,
    LLMUnavailable,
)
from app.services.retry import PermanentLLMError


@pytest.fixture(autouse=True)
def disable_retry_sleep(monkeypatch):
    monkeypatch.setattr(
        "app.services.retry.time.sleep",
        lambda delay: None,
    )


def test_primary_model_succeeds_without_fallback():
    llm = FallbackLLM(
        primary=FakeLLM("primary"),
        fallback=FakeLLM("fallback"),
    )

    response = llm.generate("What is ARPU?")

    assert response.model == "primary"
    assert response.fallback_used is False
    assert response.cost_paise == 0.0


def test_unavailable_primary_uses_fallback():
    llm = FallbackLLM(
        primary=FakeLLM("primary", should_fail=True),
        fallback=FakeLLM("fallback"),
    )

    response = llm.generate("What is ARPU?")

    assert response.model == "fallback"
    assert response.fallback_used is True


def test_failure_of_both_models_is_reported():
    llm = FallbackLLM(
        primary=FakeLLM("primary", should_fail=True),
        fallback=FakeLLM("fallback", should_fail=True),
    )

    with pytest.raises(LLMUnavailable):
        llm.generate("What is ARPU?")


def test_permanent_primary_error_does_not_use_fallback():
    primary = FakeLLM(
        "primary",
        should_fail=True,
        permanent_failure=True,
    )
    fallback = FakeLLM("fallback")

    fallback_calls = 0
    original_generate = fallback.generate

    def track_fallback(question):
        nonlocal fallback_calls
        fallback_calls += 1
        return original_generate(question)

    fallback.generate = track_fallback

    llm = FallbackLLM(
        primary=primary,
        fallback=fallback,
    )

    with pytest.raises(PermanentLLMError):
        llm.generate("What is ARPU?")

    assert fallback_calls == 0
