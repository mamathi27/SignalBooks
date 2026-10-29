
import pytest

from app.services.retry import (
    PermanentLLMError,
    TransientLLMError,
    retry_call,
)


def test_retries_then_succeeds(monkeypatch):
    attempts = 0
    delays = []

    def fake_sleep(delay):
        delays.append(delay)

    monkeypatch.setattr("app.services.retry.time.sleep", fake_sleep)
    monkeypatch.setattr(
        "app.services.retry.random.uniform",
        lambda a, b: 0,
    )

    def operation():
        nonlocal attempts
        attempts += 1

        if attempts < 3:
            raise TransientLLMError("Temporary failure")

        return "success"

    result = retry_call(operation, max_attempts=3, base_delay=0.5)

    assert result == "success"
    assert attempts == 3
    assert delays == [0.5, 1.0]


def test_exhausted_retries_raise_error(monkeypatch):
    monkeypatch.setattr("app.services.retry.time.sleep", lambda delay: None)

    attempts = 0

    def operation():
        nonlocal attempts
        attempts += 1
        raise TransientLLMError("Still unavailable")

    with pytest.raises(TransientLLMError):
        retry_call(operation, max_attempts=3)

    assert attempts == 3


def test_permanent_error_is_not_retried():
    attempts = 0

    def operation():
        nonlocal attempts
        attempts += 1
        raise PermanentLLMError("Invalid API key")

    with pytest.raises(PermanentLLMError):
        retry_call(operation)

    assert attempts == 1


def test_timeout_error_is_retried(monkeypatch):
    monkeypatch.setattr(
        "app.services.retry.time.sleep",
        lambda delay: None,
    )
    monkeypatch.setattr(
        "app.services.retry.random.uniform",
        lambda a, b: 0,
    )

    attempts = 0

    def operation():
        nonlocal attempts
        attempts += 1

        if attempts == 1:
            raise TransientLLMError("Request timed out")

        return "success"

    result = retry_call(operation, max_attempts=3)

    assert result == "success"
    assert attempts == 2
