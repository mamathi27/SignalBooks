import pytest

from app.services.llm import (
    FakeLLM,
    FallbackLLM,
    LLMStreamEvent,
    LLMUnavailable,
)
from app.services.retry import (
    PermanentLLMError,
    StreamInterruptedError,
    TransientLLMError,
)


class TrackingFakeLLM(FakeLLM):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.generate_calls = 0

    def generate(self, question):
        self.generate_calls += 1
        return super().generate(question)


class PartialFailureLLM:
    def generate(self, question):
        raise AssertionError("generate() should not be called")

    def stream(self, question):
        yield LLMStreamEvent(text="partial answer")
        raise TransientLLMError("Connection lost")


class PermanentFailureLLM:
    def generate(self, question):
        raise PermanentLLMError("Invalid API key")

    def stream(self, question):
        raise PermanentLLMError("Invalid API key")
        yield


def test_stream_uses_fallback_when_primary_fails_before_output(monkeypatch):
    monkeypatch.setattr(
        "app.services.retry.time.sleep",
        lambda delay: None,
    )

    primary = TrackingFakeLLM(
        model_name="primary",
        should_fail=True,
    )
    fallback = TrackingFakeLLM(model_name="fallback")

    events = list(FallbackLLM(primary, fallback).stream("What is ARPU?"))

    text = "".join(event.text for event in events)
    final = next(
        event.final_response
        for event in events
        if event.final_response is not None
    )

    assert "fallback" in text
    assert final.model == "fallback"
    assert final.fallback_used is True
    assert primary.generate_calls == 3
    assert fallback.generate_calls == 1


def test_stream_does_not_fallback_after_partial_output():
    fallback = TrackingFakeLLM(model_name="fallback")
    stream = FallbackLLM(
        PartialFailureLLM(),
        fallback,
    ).stream("What is ARPU?")

    assert next(stream).text == "partial answer"

    with pytest.raises(StreamInterruptedError):
        next(stream)

    assert fallback.generate_calls == 0


def test_stream_does_not_fallback_on_permanent_error():
    fallback = TrackingFakeLLM(model_name="fallback")

    with pytest.raises(PermanentLLMError):
        list(
            FallbackLLM(
                PermanentFailureLLM(),
                fallback,
            ).stream("What is ARPU?")
        )

    assert fallback.generate_calls == 0


def test_stream_raises_unavailable_when_both_models_fail(monkeypatch):
    monkeypatch.setattr(
        "app.services.retry.time.sleep",
        lambda delay: None,
    )

    primary = TrackingFakeLLM(
        model_name="primary",
        should_fail=True,
    )
    fallback = TrackingFakeLLM(
        model_name="fallback",
        should_fail=True,
    )

    with pytest.raises(LLMUnavailable):
        list(FallbackLLM(primary, fallback).stream("What is ARPU?"))

    assert primary.generate_calls == 3
    assert fallback.generate_calls == 3
