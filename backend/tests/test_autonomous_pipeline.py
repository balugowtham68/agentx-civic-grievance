"""Tests for the Autonomous Event-Driven Pipeline, Fast Acknowledgement, and Location Resolver."""

import pytest
import re
from fastapi.testclient import TestClient
from app.core.events.bus import AsyncEventBus
from app.core.events.idempotency import InMemoryIdempotencyStore
from app.core.events.schemas import DomainEvent, EventType, Job
from app.services.location.resolver import LocalCivicResolver
from app.services.location.schemas import LocationInput


def test_fast_acknowledgement_returns_under_sla(client: TestClient) -> None:
    """Citizen receives instant acknowledgement with SPN-XXXXXX tracking ID."""
    body = {
        "text": "మా వీధిలో మూడు రోజులుగా స్ట్రీట్ లైట్ పని చేయడం లేదు. లొకేషన్: మాదాపూర్, హైదరాబాద్",
        "language": "te",
        "location": "Madhapur, Hyderabad",
        "latitude": 17.4482,
        "longitude": 78.3742,
        "photo_name": "street_light.jpg",
        "photo_data": "data:image/jpeg;base64,lightimg",
        "channel": "text",
    }
    response = client.post("/api/v1/complaints/submit", json=body)
    assert response.status_code == 201, response.text
    data = response.json()

    assert "complaint_id" in data
    assert "tracking_id" in data
    assert re.match(r"^SPN-[A-F0-9]{6}$", data["tracking_id"])
    assert data["status"] == "RECEIVED"
    assert "SPANDAN AI" in data["message"]


def test_nonsense_input_rejected_with_422(client: TestClient) -> None:
    """Nonsense, spam, and non-civic inputs are rejected with 422 to prevent false complaints."""
    res = client.post("/api/v1/complaints/submit", json={"text": "asdfghjk123"})
    assert res.status_code == 422

    res_chat = client.post("/api/v1/complaints/submit", json={"text": "hello how are you?"})
    assert res_chat.status_code == 422


def test_mandatory_gps_rejected_when_missing(client: TestClient) -> None:
    """Submission without live GPS coordinates is rejected with 422."""
    res = client.post(
        "/api/v1/complaints/submit",
        json={
            "text": "Broken streetlight for 4 days on main road",
            "photo_name": "light.jpg",
            "photo_data": "data:image/jpeg;base64,data",
        },
    )
    assert res.status_code == 422
    assert "Live GPS" in res.text


def test_mandatory_photo_rejected_when_missing(client: TestClient) -> None:
    """Submission without photographic proof is rejected with 422."""
    res = client.post(
        "/api/v1/complaints/submit",
        json={
            "text": "Broken streetlight for 4 days on main road",
            "latitude": 17.448,
            "longitude": 78.374,
        },
    )
    assert res.status_code == 422
    assert "Photo proof" in res.text


def test_validate_intent_endpoint(client: TestClient) -> None:
    """Validates intent returns diagnostic questions in the requested or detected language."""
    # English test
    res = client.post(
        "/api/v1/complaints/validate-intent",
        json={"text": "Streetlight pole broken and dark at night", "language": "en"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["is_civic"] is True
    assert data["category"] == "STREETLIGHT_OUTAGE"
    assert len(data["suggested_questions"]) >= 1

    # Telugu test
    res_te = client.post(
        "/api/v1/complaints/validate-intent",
        json={"text": "మా వీధిలో స్ట్రీట్ లైట్ వెలగడం లేదు", "language": "te"},
    )
    assert res_te.status_code == 200
    data_te = res_te.json()
    assert data_te["is_civic"] is True
    assert data_te["category"] == "STREETLIGHT_OUTAGE"
    # Diagnostic questions should be in Telugu
    assert "లైట్ పరిస్థితి ఏమిటి?" in data_te["suggested_questions"][0]["question"]


def test_gps_photo_and_diagnostics_submission(client: TestClient) -> None:
    """Civic grievance with GPS, photo evidence, and diagnostic details records timeline entries."""
    body = {
        "text": "Deep potholes on the main road near junction causing accidents",
        "language": "en",
        "location": "Banjara Hills, Hyderabad",
        "latitude": 17.4156,
        "longitude": 78.4350,
        "photo_name": "pothole_photo.jpg",
        "photo_data": "data:image/jpeg;base64,12345",
        "diagnostic_details": {"condition": "Deep dangerous craters", "traffic": "High-speed road"},
    }
    submit_res = client.post("/api/v1/complaints/submit", json=body)
    assert submit_res.status_code == 201
    cid = submit_res.json()["complaint_id"]

    timeline_res = client.get(f"/api/v1/complaints/{cid}/timeline")
    assert timeline_res.status_code == 200
    stages = [e["stage"] for e in timeline_res.json()["timeline"]]
    assert "RECEIVED" in stages
    assert "GPS_LOCATED" in stages
    assert "EVIDENCE_VERIFIED" in stages


def test_complaint_timeline_endpoint(client: TestClient) -> None:
    """Timeline endpoint returns progress stages and tracking information."""
    body = {
        "text": "Broken water pipeline leaking clean water continuously on Road No 36.",
        "language": "en",
        "location": "Jubilee Hills, Hyderabad",
        "latitude": 17.4325,
        "longitude": 78.4071,
        "photo_name": "pipe_burst.jpg",
        "photo_data": "data:image/jpeg;base64,pipe",
    }
    submit_res = client.post("/api/v1/complaints/submit", json=body)
    assert submit_res.status_code == 201
    cid = submit_res.json()["complaint_id"]

    timeline_res = client.get(f"/api/v1/complaints/{cid}/timeline")
    assert timeline_res.status_code == 200
    tl_data = timeline_res.json()

    assert tl_data["complaint_id"] == cid
    assert tl_data["tracking_id"].startswith("SPN-")
    assert len(tl_data["timeline"]) >= 1
    assert tl_data["timeline"][0]["stage"] == "RECEIVED"


def test_location_confirmation_endpoint(client: TestClient) -> None:
    """Citizen can confirm or correct their resolved location."""
    submit_res = client.post(
        "/api/v1/complaints/submit",
        json={
            "text": "Garbage dump near gate",
            "location": "Koramangala",
            "latitude": 12.9352,
            "longitude": 77.6245,
            "photo_name": "dump.jpg",
            "photo_data": "data:image/jpeg;base64,dump",
        },
    )
    cid = submit_res.json()["complaint_id"]

    confirm_res = client.post(
        f"/api/v1/complaints/{cid}/location/confirm",
        json={"confirmed": True, "corrected_location": "Ward 151, Koramangala, Bengaluru"},
    )
    assert confirm_res.status_code == 200
    assert confirm_res.json()["confirmed"] is True
    assert confirm_res.json()["location"] == "Ward 151, Koramangala, Bengaluru"


def test_location_resolver_unit() -> None:
    """LocalCivicResolver resolves wards and municipal jurisdictions."""
    import asyncio

    async def _run():
        resolver = LocalCivicResolver()

        # Hyderabad test
        res_hyd = await resolver.resolve(LocationInput(text="Street 4, Madhapur, Hyderabad", source="TEXT"))
        assert res_hyd.city == "Hyderabad"
        assert res_hyd.ward == "Ward 104"
        assert res_hyd.jurisdiction_id == "GHMC-104"
        assert res_hyd.confidence > 0.8

        # Chennai test
        res_chn = await resolver.resolve(LocationInput(text="Near railway station, T Nagar, Chennai", source="TEXT"))
        assert res_chn.city == "Chennai"
        assert res_chn.ward == "Ward 134"
        assert res_chn.jurisdiction_id == "GCC-134"

        # Bengaluru test
        res_blr = await resolver.resolve(LocationInput(text="8th block Koramangala Bengaluru", source="TEXT"))
        assert res_blr.city == "Bengaluru"
        assert res_blr.ward == "Ward 151"
        assert res_blr.jurisdiction_id == "BBMP-151"

    asyncio.run(_run())


def test_idempotency_store_unit() -> None:
    """InMemoryIdempotencyStore prevents duplicate job or event execution."""
    store = InMemoryIdempotencyStore()

    # First check: not processed
    assert store.exists("event-001") is False

    # Mark processed (first time returns True)
    assert store.check_and_set("event-001", ttl_seconds=5) is True

    # Second check: exists and check_and_set returns False
    assert store.exists("event-001") is True
    assert store.check_and_set("event-001", ttl_seconds=5) is False


def test_async_event_bus() -> None:
    """AsyncEventBus dispatches domain events to subscribers."""
    import asyncio

    async def _run():
        bus = AsyncEventBus()
        received_events = []

        async def on_intake(event: DomainEvent):
            received_events.append(event)

        bus.subscribe(EventType.INTAKE_COMPLETED, on_intake)

        test_event = DomainEvent(
            event_type=EventType.INTAKE_COMPLETED,
            complaint_id="comp-123",
            payload={"issue": "Water leakage"},
        )
        await bus.publish(test_event)
        # Yield to event loop to allow task dispatched by create_task to execute
        await asyncio.sleep(0.05)

        assert len(received_events) == 1
        assert received_events[0].complaint_id == "comp-123"
        assert received_events[0].payload["issue"] == "Water leakage"

    asyncio.run(_run())
