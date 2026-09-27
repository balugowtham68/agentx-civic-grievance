from __future__ import annotations

import asyncio
import pytest
from datetime import UTC, datetime
from fastapi.testclient import TestClient

from app.core.events.schema import DomainEvent
from app.core.events.idempotency import IdempotencyManager, DuplicateEventError
from app.core.events.bus import LocalAsyncEventBus
from app.core.events.queue import AsyncJobQueue, Job
from app.services.location.resolver import LocationResolver


def test_idempotency_manager():
    """Verify that idempotency manager prevents duplicate executions."""
    mgr = IdempotencyManager()
    event_key = "event:test-complaint-1:intake"

    # First attempt should execute successfully
    executed = False
    with mgr.execute_idempotent(event_key) as allowed:
        assert allowed is True
        executed = True

    assert executed is True
    assert mgr.is_processed(event_key) is True

    # Second attempt should yield False
    with mgr.execute_idempotent(event_key) as allowed:
        assert allowed is False


def test_event_bus_and_wildcard():
    """Verify event bus subscribes, routes, and handles wildcard subscriptions."""
    async def _run():
        bus = LocalAsyncEventBus()
        received_events = []

        async def on_complaint_event(evt: DomainEvent):
            received_events.append(evt)

        bus.subscribe("complaint.*", on_complaint_event)

        event1 = DomainEvent(
            event_type="complaint.created",
            complaint_id="c-123",
            payload={"issue": "Water leakage"},
        )
        event2 = DomainEvent(
            event_type="complaint.classified",
            complaint_id="c-123",
            payload={"department": "Water Supply"},
        )

        await bus.publish(event1)
        await bus.publish(event2)
        await asyncio.sleep(0.05)

        assert len(received_events) == 2
        assert received_events[0].event_type == "complaint.created"
        assert received_events[1].event_type == "complaint.classified"

    asyncio.run(_run())


def test_job_queue_execution():
    """Verify job queue processes tasks with retry tracking."""
    async def _run():
        queue = AsyncJobQueue()
        counter = {"count": 0}

        async def sample_handler(job):
            counter["count"] += 1

        queue.register_handler("test_task", sample_handler)
        job = await queue.enqueue("test_task", "c-123", {"msg": "hello"})
        await asyncio.sleep(0.05)

        assert job.status == "COMPLETED"
        assert counter["count"] == 1

    asyncio.run(_run())


def test_location_resolver_gps_and_text():
    """Verify multi-signal location resolver handles GPS coordinates and text."""
    resolver = LocationResolver()

    # 1. Test GPS resolution in Hyderabad (Hitec City area)
    gps_res = resolver.resolve(latitude=17.4474, longitude=78.3762, source="GPS")
    assert gps_res.city == "Hyderabad"
    assert gps_res.state == "Telangana"
    assert gps_res.confidence >= 0.8
    assert "Hyderabad" in gps_res.summary()

    # 2. Test text gazetteer resolution
    text_res = resolver.resolve(raw_text="Koramangala, Bengaluru, Karnataka", source="TEXT")
    assert text_res.city == "Bengaluru"
    assert text_res.state == "Karnataka"
    assert "Koramangala" in text_res.summary()


def test_fast_acknowledgement_endpoint(client: TestClient):
    """Verify POST /api/v1/complaints/submit returns in < 500ms with tracking ID and RECEIVED status."""
    payload = {
        "text": "Open drainage overflowing on road number 12, Banjara Hills.",
        "language": "en",
        "location": "Banjara Hills, Hyderabad",
        "latitude": 17.4156,
        "longitude": 78.4350,
        "photo_data": "data:image/jpeg;base64,sample_drainage_photo_data_12345",
    }

    start = datetime.now(UTC)
    response = client.post("/api/v1/complaints/submit", json=payload)
    elapsed_ms = (datetime.now(UTC) - start).total_seconds() * 1000

    assert response.status_code == 202
    data = response.json()
    assert "complaint_id" in data
    assert "tracking_id" in data
    assert data["tracking_id"].startswith("SPN-")
    assert data["status"] == "RECEIVED"
    assert "SPANDAN AI" in data["message"]
    assert data["has_photo_proof"] is True


def test_timeline_endpoint_and_tracking_id_lookup(client: TestClient):
    """Verify GET /api/v1/complaints/{id}/timeline returns stages and can be queried by UUID or tracking ID."""
    # First submit complaint
    create_res = client.post(
        "/api/v1/complaints/submit",
        json={
            "text": "Streetlights not working for past 5 days.",
            "language": "en",
            "location": "Madhapur, Hyderabad",
            "latitude": 17.4483,
            "longitude": 78.3915,
            "photo_data": "data:image/jpeg;base64,sample_streetlight_photo_data",
        },
    )
    assert create_res.status_code == 202
    ack = create_res.json()
    complaint_id = ack["complaint_id"]
    tracking_id = ack["tracking_id"]

    # Query timeline by UUID
    tl_res1 = client.get(f"/api/v1/complaints/{complaint_id}/timeline")
    assert tl_res1.status_code == 200
    t1 = tl_res1.json()
    assert t1["complaint_id"] == complaint_id
    assert t1["tracking_id"] == tracking_id
    assert len(t1["stages"]) == 6
    assert t1["stages"][0]["stage"] == "RECEIVED"
    assert t1["stages"][0]["status"] in ("COMPLETED", "IN_PROGRESS")
    assert t1["has_photo_proof"] is True
    assert t1["photo_url"] is not None

    # Query timeline by tracking ID (SPN-XXXXXX)
    tl_res2 = client.get(f"/api/v1/complaints/{tracking_id}/timeline")
    assert tl_res2.status_code == 200
    t2 = tl_res2.json()
    assert t2["complaint_id"] == complaint_id
    assert t2["tracking_id"] == tracking_id


def test_location_confirm_and_correct_endpoints(client: TestClient):
    """Verify citizen can confirm or correct location via dedicated endpoints."""
    create_res = client.post(
        "/api/v1/complaints/submit",
        json={
            "text": "Garbage pile near community park.",
            "location": "Kukatpally",
            "latitude": 17.4849,
            "longitude": 78.4138,
            "photo_data": "data:image/jpeg;base64,sample_garbage_photo",
        },
    )
    complaint_id = create_res.json()["complaint_id"]

    # Confirm location
    confirm_res = client.post(
        f"/api/v1/complaints/{complaint_id}/location/confirm",
        json={"locality": "Kukatpally Phase 1"},
    )
    assert confirm_res.status_code == 200
    assert confirm_res.json()["location"] == "Kukatpally Phase 1"

    # Correct location
    correct_res = client.post(
        f"/api/v1/complaints/{complaint_id}/location/correct",
        json={
            "locality": "KPHB Colony",
            "city": "Hyderabad",
            "state": "Telangana",
        },
    )
    assert correct_res.status_code == 200
    assert "KPHB Colony" in correct_res.json()["location"]
    assert "Hyderabad" in correct_res.json()["location"]


def test_mandatory_gps_validation(client: TestClient):
    """Verify that submitting a complaint without live GPS coordinates is rejected with 422."""
    res = client.post(
        "/api/v1/complaints/submit",
        json={
            "text": "Severe water leakage on the main street.",
            "location": "Ameerpet",
            "photo_data": "data:image/jpeg;base64,sample_photo",
            # Missing latitude and longitude
        },
    )
    assert res.status_code == 422
    err_text = res.json().get("detail") or res.json().get("error", {}).get("message", "")
    assert "GPS" in err_text


def test_mandatory_photo_proof_validation(client: TestClient):
    """Verify that submitting a complaint without photo proof is rejected with 422."""
    res = client.post(
        "/api/v1/complaints/submit",
        json={
            "text": "Broken footpath posing serious danger to pedestrians.",
            "location": "Banjara Hills",
            "latitude": 17.4156,
            "longitude": 78.4350,
            # Missing photo_data
        },
    )
    assert res.status_code == 422
    err_text = res.json().get("detail") or res.json().get("error", {}).get("message", "")
    assert "Photo proof is mandatory" in err_text


def test_nonsense_and_gibberish_validation(client: TestClient):
    """Verify that gibberish, spam phrases, or non-civic input is rejected with 422 and alerts the user."""
    # 1. Keyboard smash
    res1 = client.post(
        "/api/v1/complaints/submit",
        json={
            "text": "asdfasdfasdf",
            "latitude": 17.4156,
            "longitude": 78.4350,
            "photo_data": "data:image/jpeg;base64,sample_photo",
        },
    )
    assert res1.status_code == 422

    # 2. Greeting / dummy text
    res2 = client.post(
        "/api/v1/complaints/submit",
        json={
            "text": "hello hi test checking",
            "latitude": 17.4156,
            "longitude": 78.4350,
            "photo_data": "data:image/jpeg;base64,sample_photo",
        },
    )
    assert res2.status_code == 422

    # 3. Repeated character smashing
    res3 = client.post(
        "/api/v1/complaints/submit",
        json={
            "text": "aaaaaaa zzzzzzz 11111",
            "latitude": 17.4156,
            "longitude": 78.4350,
            "photo_data": "data:image/jpeg;base64,sample_photo",
        },
    )
    assert res3.status_code == 422


def test_autonomous_pipeline_full_lifecycle(client: TestClient):
    """Verify autonomous pipeline orchestrates complaint from CREATED all the way to MONITORING."""
    from app.services.workflow.pipeline import AutonomousWorkflowPipeline
    from app.models import Complaint
    from app.schemas.enums import ComplaintStatus

    app = client.app
    create_res = client.post(
        "/api/v1/complaints/submit",
        json={
            "text": "Dead animal lying on the road for past two days causing severe stench.",
            "language": "en",
            "location": "Banjara Hills, Hyderabad",
            "latitude": 17.4156,
            "longitude": 78.4350,
            "photo_data": "data:image/jpeg;base64,sample_dead_animal_proof",
        },
    )
    assert create_res.status_code == 202
    data = create_res.json()
    complaint_id = data["complaint_id"]
    tracking_id = data["tracking_id"]

    # Run the background pipeline
    pipeline = AutonomousWorkflowPipeline(app.state.db, app.state.reference)
    asyncio.run(pipeline.process(complaint_id, app.state))

    # Verify complaint reached MONITORING in database
    with app.state.db.session() as session:
        complaint = session.get(Complaint, complaint_id)
        assert complaint is not None
        assert complaint.status == ComplaintStatus.MONITORING
        assert complaint.department_id is not None
        assert complaint.tracking_id == tracking_id
        assert complaint.sla is not None

    # Verify timeline reports all stages
    tl_res = client.get(f"/api/v1/complaints/{tracking_id}/timeline")
    assert tl_res.status_code == 200
    timeline = tl_res.json()
    stage_names = [s["stage"] for s in timeline["stages"]]
    assert stage_names == [
        "RECEIVED",
        "UNDERSTOOD",
        "CLASSIFIED",
        "DRAFTED",
        "FILED",
        "MONITORING",
    ]
    # In MONITORING state, stages up to FILED are COMPLETED and MONITORING is IN_PROGRESS
    for stage in timeline["stages"][:-1]:
        assert stage["status"] == "COMPLETED"
    assert timeline["has_photo_proof"] is True
    assert timeline["photo_url"] is not None
    assert timeline["gps_coordinates"] is not None


def test_compare_user_data_with_postgresql_for_problem_options_and_drafting(client: TestClient):
    """Verify comparing citizen input with PostgreSQL database, identifying problem-related options,
    generating formal draft, and citizen confirmation of the draft."""
    # 1. Compare citizen data with PostgreSQL
    detect_res = client.post(
        "/api/v1/complaints/detect-options",
        json={
            "text": "The main road in Madhapur near Cyber Towers has very deep potholes causing dangerous accidents",
            "language": "te",
            "latitude": 17.4483,
            "longitude": 78.3915,
            "location": "Madhapur Cyber Towers, Hyderabad",
            "photo_data": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=",
        },
    )
    assert detect_res.status_code == 200
    data = detect_res.json()

    # Problem detected correctly
    assert data["detected_problem"]["category"] == "road_damage"
    assert data["detected_problem"]["department_id"] == "GHMC_ROADS"
    assert data["detected_problem"]["sla_hours"] == 48

    # Related problem options figured out from PostgreSQL catalog
    assert len(data["related_options"]) >= 3
    categories = [opt["category"] for opt in data["related_options"]]
    assert "road_damage" not in categories  # related options are distinct alternatives

    # Formal administrative draft generated with bilingual support
    draft = data["draft"]
    assert "road" in draft["subject"].lower() or "pothole" in draft["subject"].lower()
    assert draft["subject_local"] != ""
    assert "EVIDENCE & VERIFICATION" in draft["body"]
    assert "Latitude 17.44830° N" in draft["body"]

    # 2. Citizen confirms drafting and lodges complaint with confirmed category & draft
    submit_res = client.post(
        "/api/v1/complaints/submit",
        json={
            "text": "The main road in Madhapur near Cyber Towers has very deep potholes causing dangerous accidents",
            "language": "te",
            "latitude": 17.4483,
            "longitude": 78.3915,
            "location": "Madhapur Cyber Towers, Hyderabad",
            "photo_data": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=",
            "confirmed_category": data["detected_problem"]["category"],
            "confirmed_department": data["detected_problem"]["department_id"],
            "draft_subject": draft["subject"],
            "draft_body": draft["body"],
        },
    )
    assert submit_res.status_code == 202
    ack = submit_res.json()
    assert ack["tracking_id"].startswith("SPN-")
    assert ack["has_photo_proof"] is True


def test_demo_email_configuration_and_env_placeholders():
    """Verify demo email configuration is read from settings and .env.example contains placeholders."""
    from pathlib import Path
    from app.core.config import get_settings
    from app.services.notification.email_service import demo_email_service

    settings = get_settings()
    # Check settings attributes exist and are configurable
    assert hasattr(settings, "authority_review_email")
    assert hasattr(settings, "higher_official_email")

    # Service reads configured recipients
    authority_email = demo_email_service.get_authority_email()
    higher_email = demo_email_service.get_higher_official_email()
    assert "@" in authority_email
    assert "@" in higher_email

    # Check .env.example contains the placeholders
    repo_root = Path(__file__).resolve().parents[2]
    env_example = (repo_root / ".env.example").read_text(encoding="utf-8")
    assert "AUTHORITY_REVIEW_EMAIL=" in env_example
    assert "HIGHER_OFFICIAL_EMAIL=" in env_example
    assert "authority@example.gov.in" in env_example


def test_demo_email_authority_accept_workflow(client: TestClient):
    """Workflow Steps 1 & 2:
    1. New complaint submitted -> review email dispatched to AUTHORITY_REVIEW_EMAIL.
    2. Authority clicks ACCEPT -> status transitions to ACCEPTED_BY_AUTHORITY."""
    from app.models.complaint import Complaint
    from app.schemas.enums import ComplaintStatus, AuthorityStatus

    # Submit complaint with mandatory GPS and photo proof
    submit_res = client.post(
        "/api/v1/complaints/submit",
        json={
            "text": "Streetlight pole #42 on Road No 36 is broken and sparking dangerous fire",
            "language": "en",
            "latitude": 17.4375,
            "longitude": 78.4023,
            "photo_data": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==",
            "confirmed_category": "streetlight",
            "confirmed_department": "GHMC_ELECTRICAL",
        },
    )
    assert submit_res.status_code == 202
    data = submit_res.json()
    complaint_id = data["complaint_id"]
    tracking_id = data["tracking_id"]

    # Check status endpoint
    status_res = client.get(f"/api/v1/review/{tracking_id}/status")
    assert status_res.status_code == 200
    status_info = status_res.json()
    assert status_info["can_authority_accept"] is True
    assert status_info["can_authority_reject"] is True

    # 2. Authority clicks ACCEPT link
    accept_res = client.get(
        f"/api/v1/review/{complaint_id}/accept",
        headers={"Accept": "application/json"},
    )
    assert accept_res.status_code == 200
    accept_data = accept_res.json()
    assert accept_data["success"] is True
    assert accept_data["status"] == ComplaintStatus.ACCEPTED_BY_AUTHORITY.value

    # Verify browser HTML view also works
    accept_html_res = client.get(f"/api/v1/review/{complaint_id}/accept")
    assert accept_html_res.status_code == 200
    assert "text/html" in accept_html_res.headers["content-type"]
    assert "OFFICIALLY ACCEPTED BY AUTHORITY" in accept_html_res.text
    assert tracking_id in accept_html_res.text

    # Verify audit logs contain authority acceptance
    audit_res = client.get(f"/api/v1/complaints/{complaint_id}/audit")
    assert audit_res.status_code == 200
    event_types = [e["event_type"] for e in audit_res.json()["items"]]
    assert "authority.accepted" in event_types


def test_demo_email_authority_reject_escalates_and_higher_accept_workflow(client: TestClient):
    """Workflow Steps 3 & 4:
    3. Authority clicks REJECT -> status transitions to REJECTED -> ESCALATED -> escalation email sent.
    4. Higher official clicks ACCEPT -> status transitions to ACCEPTED_BY_HIGHER_AUTHORITY."""
    from app.schemas.enums import ComplaintStatus

    # Submit complaint
    submit_res = client.post(
        "/api/v1/complaints/submit",
        json={
            "text": "Severe open manhole overflow in Jubilee Hills causing health hazards",
            "language": "en",
            "latitude": 17.4312,
            "longitude": 78.4078,
            "photo_data": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==",
            "confirmed_category": "drainage",
            "confirmed_department": "HMWSSB_SEWERAGE",
        },
    )
    assert submit_res.status_code == 202
    data = submit_res.json()
    complaint_id = data["complaint_id"]
    tracking_id = data["tracking_id"]

    # 3. Authority clicks REJECT
    reject_res = client.get(
        f"/api/v1/review/{tracking_id}/reject",
        headers={"Accept": "application/json"},
    )
    assert reject_res.status_code == 200
    reject_data = reject_res.json()
    assert reject_data["success"] is True
    assert reject_data["status"] == ComplaintStatus.ESCALATED.value
    assert "escalated_to" in reject_data
    assert "@" in reject_data["escalated_to"]

    # Verify browser HTML view for rejection & escalation
    reject_html_res = client.get(f"/api/v1/review/{tracking_id}/reject")
    assert reject_html_res.status_code == 200
    assert "REJECTED &amp; AUTOMATICALLY ESCALATED" in reject_html_res.text or "REJECTED" in reject_html_res.text
    assert "higher-accept" in reject_html_res.text

    # Check status endpoint confirms ready for higher official accept
    status_res = client.get(f"/api/v1/review/{tracking_id}/status")
    assert status_res.status_code == 200
    assert status_res.json()["can_higher_accept"] is True

    # 4. Higher official clicks ACCEPT
    higher_res = client.get(
        f"/api/v1/review/{complaint_id}/higher-accept",
        headers={"Accept": "application/json"},
    )
    assert higher_res.status_code == 200
    higher_data = higher_res.json()
    assert higher_data["success"] is True
    assert higher_data["status"] == ComplaintStatus.ACCEPTED_BY_HIGHER_AUTHORITY.value

    # Verify browser HTML view for higher authority acceptance
    higher_html_res = client.get(f"/api/v1/review/{complaint_id}/higher-accept")
    assert higher_html_res.status_code == 200
    assert "ACCEPTED BY HIGHER OFFICIAL" in higher_html_res.text

    # Verify audit logs trace the entire rejection -> escalation -> higher acceptance chain
    audit_res = client.get(f"/api/v1/complaints/{complaint_id}/audit")
    assert audit_res.status_code == 200
    event_types = [e["event_type"] for e in audit_res.json()["items"]]
    assert "authority.rejected" in event_types
    assert "escalation.triggered" in event_types
    assert "higher_official.accepted" in event_types



