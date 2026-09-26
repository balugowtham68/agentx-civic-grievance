"""Phase 1-4 consolidation: the complete citizen journey end to end, plus the negative
cases, across an application restart. Offline (no API keys, local knowledge base).

Citizen input -> confirmation -> classification (department, jurisdiction) -> draft
-> validation -> citizen edits (v2, v3) -> approval -> restart -> everything persisted.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.database.session import SchemaMismatchError
from app.main import create_app

V1 = "/api/v1"
TEXT = "Street light on Main Road has not been working for three days."


def test_complete_citizen_journey_survives_a_restart(settings: Settings) -> None:
    with TestClient(create_app(settings)) as client:
        intake = client.post(f"{V1}/intake/text", json={"raw_text": TEXT}).json()
        cid = intake["complaint_id"]
        assert (intake["status"], intake["processing_mode"]) == ("UNDERSTANDING", "OFFLINE_RULE")
        assert client.post(f"{V1}/intake/{cid}/confirm").json()["status"] == "UNDERSTOOD"

        classification = client.post(f"{V1}/classification/{cid}/run").json()
        assert (classification["classification_status"], classification["category"]) == ("CLASSIFIED", "streetlight")
        assert classification["responsible_department"]["department_id"] == "DEPT-ELECTRICAL"
        assert classification["jurisdiction"]["jurisdiction_id"] == "WARD-7"

        v1 = client.post(f"{V1}/drafting/{cid}/run").json()["current"]
        assert (v1["version"], v1["validation_status"]) == (1, "VALID")
        v2 = client.post(f"{V1}/drafting/{cid}/edit", json={"based_on_version": 1, "subject": "Streetlight on Main Road not working"}).json()
        v3 = client.post(f"{V1}/drafting/{cid}/edit", json={
            "based_on_version": 2, "summary": "It was repaired previously but stopped working again.",
        }).json()
        assert (v2["current"]["version"], v3["current"]["version"]) == (2, 3)
        assert v3["current"]["validation_status"] == "NEEDS_REVIEW"
        approved = client.post(f"{V1}/drafting/{cid}/approve", json={"version": 3}).json()
        assert (approved["status"], approved["approved_version"]) == ("DRAFTED", 3)

    with TestClient(create_app(settings)) as client:  # restart: same database, same knowledge base
        complaint = client.get(f"{V1}/complaints/{cid}").json()
        assert (complaint["status"], complaint["category"], complaint["department_id"], complaint["jurisdiction_id"]) == (
            "DRAFTED", "streetlight", "DEPT-ELECTRICAL", "WARD-7")
        assert complaint["citizen_input"] == TEXT and complaint["tracking_id"] is None
        assert complaint["drafted_complaint"]["draft_version"] == 3
        view = client.get(f"{V1}/drafting/{cid}").json()
        assert [v["version"] for v in view["versions"]] == [1, 2, 3] and view["approved_version"] == 3
        assert client.get(f"{V1}/drafting/{cid}/versions/1").json()["origin"] == "generated"
        assert client.get(f"{V1}/intake/{cid}").json()["citizen_confirmation_status"] == "CONFIRMED"
        assert client.get(f"{V1}/classification/{cid}").json()["classification_status"] == "CLASSIFIED"
        events = [e["event_type"] for e in client.get(f"{V1}/complaints/{cid}/audit").json()["items"]]
        for expected in ("intake.received", "intake.confirmed", "classification.started", "classification.completed",
                         "drafting.generated", "drafting.edited", "drafting.version_created", "drafting.approved",
                         "complaint.drafted"):
            assert expected in events, expected
        assert not any(e.startswith(("complaint.filed", "sla.", "escalation.", "monitoring.")) for e in events)


@pytest.mark.parametrize(
    ("step", "text"),
    [
        ("unconfirmed", TEXT),
        ("missing location", "Street light is not working"),
    ],
)
def test_nothing_advances_without_confirmation(client: TestClient, step: str, text: str) -> None:
    cid = client.post(f"{V1}/intake/text", json={"raw_text": text}).json()["complaint_id"]
    assert client.post(f"{V1}/classification/{cid}/run").status_code == 409
    assert client.post(f"{V1}/drafting/{cid}/run").status_code == 409
    if step == "missing location":
        assert client.post(f"{V1}/intake/{cid}/confirm").status_code == 409


def test_unexpected_errors_are_safe(client: TestClient) -> None:
    """A crash inside a service returns a generic error: no stack trace, no internals."""
    def boom(*args: object, **kwargs: object) -> None:
        raise RuntimeError("internal detail /etc/secret-path SELECT * FROM complaints")

    client.app.state.knowledge.status = boom  # type: ignore[attr-defined]
    response = client.get(f"{V1}/classification/knowledge-base")
    assert response.status_code == 500
    body = response.text
    assert response.json()["error"]["code"] == "internal_error"
    assert "Traceback" not in body and "secret-path" not in body and "SELECT" not in body


def test_outdated_local_database_fails_clearly_at_start_up(settings: Settings, tmp_path: Path) -> None:
    old = tmp_path / "old.db"
    with sqlite3.connect(old) as connection:  # a 'complaints' table from an older build, missing columns
        connection.execute("CREATE TABLE complaints (id VARCHAR(36) PRIMARY KEY, citizen_input TEXT)")
    outdated = settings.model_copy(update={"database_url": f"sqlite:///{old}"})
    with pytest.raises(SchemaMismatchError, match="older SPANDAN AI build"):
        with TestClient(create_app(outdated)):
            pass
    with sqlite3.connect(old) as connection:  # never modified destructively
        assert [r[1] for r in connection.execute("PRAGMA table_info(complaints)")] == ["id", "citizen_input"]


def test_unicode_survives_the_whole_journey(client: TestClient) -> None:
    """Zero-width joiners (Malayalam chillu), combining marks and emoji are kept exactly."""
    text = "ഗാന്ധി നഗറില്‍ പൈപ്പ് പൊട്ടി വെള്ളം ചോരുന്നു 😟"
    intake = client.post(f"{V1}/intake/text", json={"raw_text": text}).json()
    cid = intake["complaint_id"]
    assert intake["original_text"] == text and intake["language"]["language"] == "ml"
    assert client.post(f"{V1}/intake/{cid}/confirm").status_code == 200
    assert client.post(f"{V1}/classification/{cid}/run").json()["category"] == "water_leakage"
    current = client.post(f"{V1}/drafting/{cid}/run").json()["current"]
    assert current["citizen_statement"] == text and text in current["body"]
    assert client.get(f"{V1}/complaints/{cid}").json()["citizen_input"] == text


def test_dangerous_invisible_characters_are_removed_but_joiners_kept() -> None:
    from app.core.security import sanitize_text

    assert sanitize_text("abc‮def\u0000") == "abcdef"  # bidi override and NUL dropped
    assert sanitize_text("क्‍ष") == "क्‍ष"  # ZWJ kept
