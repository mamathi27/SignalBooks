import random
import time
from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")

TRANSIENT_HTTP_STATUS_CODES = {429, 500, 502, 503, 504}
PERMANENT_HTTP_STATUS_CODES = {400, 401, 403, 404}

MAX_BACKOFF_SECONDS = 8.0


class TransientLLMError(Exception):
    """An error that may succeed if the operation is retried."""


class PermanentLLMError(Exception):
    """An error that should not be retried."""


def classify_http_status(status_code: int) -> type[Exception]:
    """Classify an HTTP status code for retry decisions."""
    if status_code in TRANSIENT_HTTP_STATUS_CODES:
        return TransientLLMError

    if status_code in PERMANENT_HTTP_STATUS_CODES:
        return PermanentLLMError

    if 500 <= status_code <= 599:
        return TransientLLMError

    return PermanentLLMError


def retry_call(
    operation: Callable[[], T],
    *,
    max_attempts: int = 3,
    base_delay: float = 0.5,
) -> T:
    """Retry transient failures using capped exponential full jitter."""
    if max_attempts < 1:
        raise ValueError("max_attempts must be at least 1")

    if base_delay < 0:
        raise ValueError("base_delay cannot be negative")

    for attempt in range(max_attempts):
        try:
            return operation()

        except TransientLLMError:
            if attempt == max_attempts - 1:
                raise

            backoff_limit = min(
                MAX_BACKOFF_SECONDS,
                base_delay * (2 ** attempt),
            )

            delay = random.uniform(0, backoff_limit)
            time.sleep(delay)

    raise RuntimeError("Retry loop ended unexpectedly.")
