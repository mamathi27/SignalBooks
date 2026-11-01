import pytest

from app.services.retry import (
    MAX_BACKOFF_SECONDS,
    PermanentLLMError,
    TransientLLMError,
    retry_call,
)


def test_retries_then_succeeds(monkeypatch):
    attempts = 0
    delays = []

    monkeypatch.setattr(
        "app.services.retry.time.sleep",
        delays.append,
    )
    monkeypatch.setattr(
        "app.services.retry.random.uniform",
        lambda low, high: high,
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
    monkeypatch.setattr(
        "app.services.retry.time.sleep",
        lambda delay: None,
    )

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
        lambda low, high: 0,
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


def test_full_jitter_stays_within_backoff_limit(monkeypatch):
    delays = []

    monkeypatch.setattr(
        "app.services.retry.time.sleep",
        delays.append,
    )
    monkeypatch.setattr(
        "app.services.retry.random.uniform",
        lambda low, high: high,
    )

    def operation():
        raise TransientLLMError("Temporary failure")

    with pytest.raises(TransientLLMError):
        retry_call(operation, max_attempts=6, base_delay=2)

    assert delays == [2, 4, 8, 8, 8]
    assert all(0 <= delay <= MAX_BACKOFF_SECONDS for delay in delays)


def test_negative_base_delay_is_rejected():
    with pytest.raises(ValueError):
        retry_call(lambda: "success", base_delay=-1)


def test_zero_attempts_are_rejected():
    with pytest.raises(ValueError):
        retry_call(lambda: "success", max_attempts=0)
