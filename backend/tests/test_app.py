"""Application start-up, health and API documentation."""

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


def test_health_reports_running_service_and_database(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "SPANDAN AI"  # project renamed from AGENT X (Phase 2 brief)
    assert body["database"] == "ok"
    assert body["environment"] == "test"


def test_health_never_exposes_secrets(settings: Settings) -> None:
    settings = settings.model_copy(update={"gemini_api_key": "sk-super-secret-value"})
    with TestClient(create_app(settings)) as client:
        text = client.get("/health").text

    assert "sk-super-secret-value" not in text
    assert client.get("/health").json()["configuration"]["gemini_configured"] is True


def test_health_degrades_when_database_unreachable(client: TestClient) -> None:
    client.app.state.db.is_reachable = lambda: False  # type: ignore[attr-defined]

    response = client.get("/health")

    assert response.status_code == 503
    assert response.json()["database"] == "unavailable"


def test_openapi_and_docs_are_served(client: TestClient) -> None:
    assert client.get("/docs").status_code == 200
    schema = client.get("/openapi.json").json()
    assert "/health" in schema["paths"]
    assert "/api/v1/complaints" in schema["paths"]
    assert "ComplaintRead" in schema["components"]["schemas"]


def test_every_response_carries_a_request_id(client: TestClient) -> None:
    response = client.get("/health", headers={"X-Request-ID": "demo-123"})

    assert response.headers["X-Request-ID"] == "demo-123"
    assert client.get("/health").headers["X-Request-ID"]


def test_cors_allows_configured_frontend_origin_only(client: TestClient) -> None:
    allowed = client.options(
        "/health",
        headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "GET"},
    )
    blocked = client.options(
        "/health",
        headers={"Origin": "http://evil.example", "Access-Control-Request-Method": "GET"},
    )

    assert allowed.headers.get("access-control-allow-origin") == "http://localhost:5173"
    assert "access-control-allow-origin" not in blocked.headers
