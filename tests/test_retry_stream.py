import pytest

from app.services.retry import (
    PermanentLLMError,
    StreamInterruptedError,
    TransientLLMError,
    retry_stream,
)


def test_retry_stream_retries_before_first_output(monkeypatch):
    attempts = 0
    sleeps = []

    def operation():
        nonlocal attempts
        attempts += 1

        if attempts == 1:
            raise TransientLLMError("Temporary outage")

        yield "hello"
        yield "world"

    monkeypatch.setattr(
        "app.services.retry.time.sleep",
        lambda delay: sleeps.append(delay),
    )

    result = list(
        retry_stream(
            operation,
            has_output=bool,
            max_attempts=3,
            base_delay=0.5,
        )
    )

    assert result == ["hello", "world"]
    assert attempts == 2
    assert len(sleeps) == 1


def test_retry_stream_does_not_restart_after_output(monkeypatch):
    attempts = 0

    def operation():
        nonlocal attempts
        attempts += 1
        yield "partial answer"
        raise TransientLLMError("Connection lost")

    monkeypatch.setattr(
        "app.services.retry.time.sleep",
        lambda delay: None,
    )

    stream = retry_stream(
        operation,
        has_output=bool,
        max_attempts=3,
    )

    assert next(stream) == "partial answer"

    with pytest.raises(StreamInterruptedError):
        next(stream)

    assert attempts == 1


def test_retry_stream_does_not_retry_permanent_errors():
    attempts = 0

    def operation():
        nonlocal attempts
        attempts += 1
        raise PermanentLLMError("Invalid API key")
        yield "unreachable"

    with pytest.raises(PermanentLLMError):
        list(
            retry_stream(
                operation,
                has_output=bool,
                max_attempts=3,
            )
        )

    assert attempts == 1


def test_retry_stream_stops_after_max_attempts(monkeypatch):
    attempts = 0

    def operation():
        nonlocal attempts
        attempts += 1
        raise TransientLLMError("Still unavailable")
        yield "unreachable"

    monkeypatch.setattr(
        "app.services.retry.time.sleep",
        lambda delay: None,
    )

    with pytest.raises(TransientLLMError):
        list(
            retry_stream(
                operation,
                has_output=bool,
                max_attempts=3,
            )
        )

    assert attempts == 3
