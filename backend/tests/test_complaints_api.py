"""Complaint API: creation, validation, reads, audit and error format."""

from fastapi.testclient import TestClient


def _create(client: TestClient, **overrides: object) -> dict:
    body = {"citizen_input": "Streetlight near Ramalayam temple not working for 5 days"}
    body.update(overrides)
    response = client.post("/api/v1/complaints", json=body)
    assert response.status_code == 201, response.text
    return response.json()


def test_create_complaint_returns_created_state(client: TestClient) -> None:
    complaint = _create(client, language="te", channel="voice")

    assert complaint["status"] == "CREATED"
    assert complaint["authority_status"] == "NONE"
    assert complaint["escalation_state"] == "NONE"
    assert complaint["input_channel"] == "voice"
    assert complaint["tracking_id"] is None  # only the mock government API issues one


def test_created_complaint_can_be_read_listed_and_audited(client: TestClient) -> None:
    created = _create(client)

    fetched = client.get(f"/api/v1/complaints/{created['id']}").json()
    listed = client.get("/api/v1/complaints").json()
    audit = client.get(f"/api/v1/complaints/{created['id']}/audit").json()
    status = client.get(f"/api/v1/complaints/{created['id']}/status").json()

    assert fetched["id"] == created["id"]
    assert listed["total"] == 1 and listed["items"][0]["id"] == created["id"]
    assert audit["total"] == 1
    assert audit["items"][0]["event_type"] == "complaint.created"
    assert status["status"] == "CREATED" and status["sla"] is None


def test_list_filters_by_status(client: TestClient) -> None:
    _create(client)

    assert client.get("/api/v1/complaints", params={"status": "CREATED"}).json()["total"] == 1
    assert client.get("/api/v1/complaints", params={"status": "ESCALATED"}).json()["total"] == 0


def test_markup_is_stripped_but_local_script_kept(client: TestClient) -> None:
    complaint = _create(
        client, citizen_input="<script>alert(1)</script>వీధి దీపం <b>పనిచేయడం లేదు</b>"
    )

    assert complaint["citizen_input"] == "వీధి దీపం పనిచేయడం లేదు"


def test_empty_or_markup_only_input_is_rejected(client: TestClient) -> None:
    for text in ["", "  ", "<b></b><i></i>"]:
        response = client.post("/api/v1/complaints", json={"citizen_input": text})
        assert response.status_code == 422, text
        assert response.json()["error"]["code"] == "validation_error"


def test_invalid_requests_return_structured_field_errors(client: TestClient) -> None:
    response = client.post(
        "/api/v1/complaints",
        json={"citizen_input": "x" * 2001, "language": "Telugu!!", "channel": "fax"},
    )

    assert response.status_code == 422
    error = response.json()["error"]
    fields = {d["field"] for d in error["details"]}
    assert {"citizen_input", "language", "channel"} <= fields
    assert error["request_id"]


def test_invalid_query_parameters_rejected(client: TestClient) -> None:
    assert client.get("/api/v1/complaints", params={"limit": 0}).status_code == 422
    assert client.get("/api/v1/complaints", params={"status": "DONE"}).status_code == 422


def test_unknown_complaint_and_tracking_id_return_404(client: TestClient) -> None:
    for path in [
        "/api/v1/complaints/does-not-exist",
        "/api/v1/complaints/does-not-exist/audit",
        "/api/v1/track/CIV-2026-9999",
    ]:
        response = client.get(path)
        assert response.status_code == 404, path
        assert response.json()["error"]["code"] == "not_found"


def test_unknown_route_uses_same_error_format(client: TestClient) -> None:
    response = client.get("/api/v1/nope")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_unexpected_errors_hide_internals(client: TestClient) -> None:
    @client.app.get("/boom")  # type: ignore[attr-defined]
    def boom() -> None:
        raise RuntimeError("database password=hunter2 leaked in trace")

    response = client.get("/boom")

    assert response.status_code == 500
    error = response.json()["error"]
    assert error["code"] == "internal_error"
    assert error["message"] == "An unexpected error occurred"
    assert "hunter2" not in response.text
    assert "Traceback" not in response.text
