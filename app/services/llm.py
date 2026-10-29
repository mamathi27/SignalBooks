
from dataclasses import dataclass
from typing import Protocol

from app.services.retry import (
    PermanentLLMError,
    TransientLLMError,
    retry_call,
)


@dataclass
class LLMResponse:
    answer: str
    model: str
    input_tokens: int
    output_tokens: int
    cost_paise: float
    latency_ms: int
    fallback_used: bool = False


class LLMUnavailable(Exception):
    """Raised when a model cannot provide a response."""


class LLMClient(Protocol):
    """Interface that every LLM implementation must provide."""

    def generate(self, question: str) -> LLMResponse:
        ...


class FakeLLM:
    """Deterministic mock model for local development and CI."""

    def __init__(
        self,
        model_name: str = "fake-small",
        should_fail: bool = False,
        permanent_failure: bool = False,
    ):
        self.model_name = model_name
        self.should_fail = should_fail
        self.permanent_failure = permanent_failure

    def generate(self, question: str) -> LLMResponse:
        if self.should_fail:
            if self.permanent_failure:
                raise PermanentLLMError("Simulated invalid API key.")

            raise TransientLLMError("Simulated temporary model outage.")

        answer = (
            f"[Simulated answer from {self.model_name}] "
            f"You asked: {question}"
        )

        return LLMResponse(
            answer=answer,
            model=self.model_name,
            input_tokens=len(question.split()),
            output_tokens=len(answer.split()),
            cost_paise=0.0,
            latency_ms=0,
        )


def _generate_with_retry(
    model: LLMClient,
    question: str,
) -> LLMResponse:
    """Retry transient failures, but never retry permanent failures."""

    try:
        return retry_call(
            lambda: model.generate(question),
            max_attempts=3,
        )
    except TransientLLMError as exc:
        raise LLMUnavailable(str(exc)) from exc


class FallbackLLM:
    """Retry the primary model, then fall back if it remains unavailable."""

    def __init__(
        self,
        primary: LLMClient,
        fallback: LLMClient,
    ):
        self.primary = primary
        self.fallback = fallback

    def generate(self, question: str) -> LLMResponse:
        try:
            return _generate_with_retry(self.primary, question)
        except LLMUnavailable:
            response = _generate_with_retry(self.fallback, question)
            response.fallback_used = True
            return response
