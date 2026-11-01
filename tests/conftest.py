import pytest
from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.main import app


@pytest.fixture
def client():
    app.dependency_overrides[get_settings] = lambda: Settings(
        app_name="examate-rag",
        environment="test",
        llm_provider="fake",
        llm_api_key="",
        llm_model="fake-primary",
        llm_fallback_model="fake-fallback",
    )
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
