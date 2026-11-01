from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app

client = TestClient(app)


def test_ready_returns_503_when_database_url_is_missing():
    settings = get_settings().model_copy(update={"database_url": ""})

    app.dependency_overrides[get_settings] = lambda: settings

    try:
        response = client.get("/ready")

        assert response.status_code == 503
        assert response.json()["detail"]["reason"] == (
            "DATABASE_URL is not configured"
        )
    finally:
        app.dependency_overrides.clear()


@patch("app.main.psycopg.connect")
def test_ready_returns_200_when_postgres_and_pgvector_are_available(
    mock_connect,
):
    settings = get_settings().model_copy(
        update={"database_url": "postgresql://test:test@localhost/test"}
    )

    connection = MagicMock()
    cursor = MagicMock()

    mock_connect.return_value.__enter__.return_value = connection
    connection.cursor.return_value.__enter__.return_value = cursor
    cursor.fetchone.return_value = ("0.8.0",)

    app.dependency_overrides[get_settings] = lambda: settings

    try:
        response = client.get("/ready")

        assert response.status_code == 200
        assert response.json()["status"] == "ready"
        assert response.json()["database"] == "connected"
        assert response.json()["pgvector"] == "available"
        assert response.json()["pgvector_version"] == "0.8.0"
        mock_connect.assert_called_once()
    finally:
        app.dependency_overrides.clear()


@patch("app.main.psycopg.connect")
def test_ready_returns_503_when_pgvector_is_missing(mock_connect):
    settings = get_settings().model_copy(
        update={"database_url": "postgresql://test:test@localhost/test"}
    )

    connection = MagicMock()
    cursor = MagicMock()

    mock_connect.return_value.__enter__.return_value = connection
    connection.cursor.return_value.__enter__.return_value = cursor
    cursor.fetchone.return_value = None

    app.dependency_overrides[get_settings] = lambda: settings

    try:
        response = client.get("/ready")

        assert response.status_code == 503
        assert response.json()["detail"]["reason"] == (
            "pgvector extension is not installed"
        )
    finally:
        app.dependency_overrides.clear()


@patch("app.main.psycopg.connect")
def test_ready_returns_503_when_database_connection_fails(mock_connect):
    import psycopg

    settings = get_settings().model_copy(
        update={"database_url": "postgresql://test:test@localhost/test"}
    )

    mock_connect.side_effect = psycopg.OperationalError(
        "Database unavailable"
    )

    app.dependency_overrides[get_settings] = lambda: settings

    try:
        response = client.get("/ready")

        assert response.status_code == 503
        assert response.json()["detail"]["reason"] == (
            "PostgreSQL connection or query failed"
        )
    finally:
        app.dependency_overrides.clear()
