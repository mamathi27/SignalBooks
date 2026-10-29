
import pytest

from app.services.retry import (
    PermanentLLMError,
    TransientLLMError,
    classify_http_status,
)


@pytest.mark.parametrize(
    "status_code",
    [429, 500, 502, 503, 504, 599],
)
def test_transient_http_status_codes(status_code):
    assert classify_http_status(status_code) is TransientLLMError


@pytest.mark.parametrize(
    "status_code",
    [200, 400, 401, 403, 404],
)
def test_permanent_http_status_codes(status_code):
    assert classify_http_status(status_code) is PermanentLLMError
