import random
import time
from collections.abc import Callable, Iterator
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



class StreamInterruptedError(TransientLLMError):
    """A transient failure after streamed output has already been emitted."""


def retry_stream(
    operation: Callable[[], Iterator[T]],
    *,
    has_output: Callable[[T], bool],
    max_attempts: int = 3,
    base_delay: float = 0.5,
) -> Iterator[T]:
    """Retry a stream only while no user-visible output has been emitted."""
    if max_attempts < 1:
        raise ValueError("max_attempts must be at least 1")

    if base_delay < 0:
        raise ValueError("base_delay cannot be negative")

    for attempt in range(max_attempts):
        emitted_output = False

        try:
            for item in operation():
                if has_output(item):
                    emitted_output = True

                yield item

            return

        except StreamInterruptedError:
            raise

        except TransientLLMError as exc:
            if emitted_output:
                raise StreamInterruptedError(str(exc)) from exc

            if attempt == max_attempts - 1:
                raise

            backoff_limit = min(
                MAX_BACKOFF_SECONDS,
                base_delay * (2 ** attempt),
            )
            time.sleep(random.uniform(0, backoff_limit))

    raise RuntimeError("Streaming retry loop ended unexpectedly.")
