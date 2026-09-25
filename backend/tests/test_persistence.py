"""Database initialisation, complaint aggregate and audit persistence."""

from datetime import timedelta

import pytest
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError

from app.database import Database
from app.models import AuditEvent, Complaint, EscalationRecord, SLARecord
from app.repositories import (
    AuditRepository,
    ComplaintRepository,
    EscalationRepository,
    SLARepository,
)
from app.schemas.audit import AuditEventCreate
from app.schemas.complaint import ComplaintCreateRequest, ComplaintRead
from app.schemas.enums import (
    ActorType,
    AuditEventType,
    ComplaintStatus,
    EscalationState,
    InputChannel,
    SLAStage,
)
from app.services.complaint_service import ComplaintService
from tests.conftest import FixedClock


def _complaint(clock: FixedClock) -> Complaint:
    now = clock.now()
    return Complaint(
        citizen_input="Streetlight near temple not working",
        input_channel=InputChannel.TEXT,
        created_at=now,
        updated_at=now,
    )


def test_schema_creates_all_tables(database: Database) -> None:
    tables = set(inspect(database.engine).get_table_names())

    assert {"complaints", "sla_records", "escalations", "audit_events"} <= tables
    assert database.is_reachable()


def test_complaint_defaults_and_round_trip(database: Database, clock: FixedClock) -> None:
    with database.session() as session:
        complaint_id = ComplaintRepository(session).add(_complaint(clock)).id

    with database.session() as session:
        stored = ComplaintRepository(session).get(complaint_id)
        assert stored is not None
        read = ComplaintRead.model_validate(stored)

    assert read.status is ComplaintStatus.CREATED
    assert read.tracking_id is None
    assert read.escalation_state is EscalationState.NONE
    assert read.sla_start is None
    assert read.created_at == clock.now()  # timezone-aware round trip


def test_complaint_exposes_sla_start_and_deadline(database: Database, clock: FixedClock) -> None:
    with database.session() as session:
        complaint = ComplaintRepository(session).add(_complaint(clock))
        SLARepository(session).add(
            SLARecord(
                complaint_id=complaint.id,
                policy_id="SLA-STREETLIGHT",
                started_at=clock.now(),
                warning_at=clock.now() + timedelta(hours=48),
                deadline_at=clock.now() + timedelta(hours=72),
                stage=SLAStage.ON_TRACK,
            )
        )
        complaint_id = complaint.id

    with database.session() as session:
        stored = ComplaintRepository(session).get(complaint_id)
        assert stored is not None
        assert stored.sla_start == clock.now()
        assert stored.sla_deadline == clock.now() + timedelta(hours=72)


def test_same_escalation_level_cannot_be_stored_twice(database: Database, clock: FixedClock) -> None:
    def escalation(complaint_id: str) -> EscalationRecord:
        return EscalationRecord(
            complaint_id=complaint_id,
            level=1,
            policy_id="ESC-DEFAULT",
            target_authority_id="AUTH-WARD-12-OFFICER",
            reason="SLA breached",
            created_at=clock.now(),
            updated_at=clock.now(),
        )

    with database.session() as session:
        complaint = ComplaintRepository(session).add(_complaint(clock))
        EscalationRepository(session).add(escalation(complaint.id))
        complaint_id = complaint.id

    with pytest.raises(IntegrityError):
        with database.session() as session:
            EscalationRepository(session).add(escalation(complaint_id))

    with database.session() as session:
        assert len(EscalationRepository(session).list_for_complaint(complaint_id)) == 1
        assert ComplaintRepository(session).get(complaint_id).escalation_state is EscalationState.ESCALATED  # type: ignore[union-attr]


def test_naive_datetimes_are_rejected(database: Database) -> None:
    from datetime import datetime

    with pytest.raises(Exception, match="Naive datetimes"):
        with database.session() as session:
            ComplaintRepository(session).add(
                Complaint(
                    citizen_input="x" * 5,
                    input_channel=InputChannel.TEXT,
                    created_at=datetime(2026, 1, 1),
                    updated_at=datetime(2026, 1, 1),
                )
            )


def test_audit_events_persist_in_order_with_evidence(database: Database, clock: FixedClock) -> None:
    with database.session() as session:
        complaint_id = ComplaintRepository(session).add(_complaint(clock)).id
        repo = AuditRepository(session)
        repo.append(
            AuditEventCreate(
                complaint_id=complaint_id,
                event_type=AuditEventType.COMPLAINT_CREATED,
                actor_type=ActorType.CITIZEN,
                actor_name="citizen",
                summary="created",
            ),
            occurred_at=clock.now(),
        )
        clock.advance(hours=1)
        repo.append(
            AuditEventCreate(
                complaint_id=complaint_id,
                event_type=AuditEventType.COMPLAINT_CLASSIFIED,
                actor_type=ActorType.AGENT,
                actor_name="classification",
                summary="classified",
                evidence=[{"doc_id": "KB-RULE-STREETLIGHT-01", "snippet": "..."}],
            ),
            occurred_at=clock.now(),
        )

    with database.session() as session:
        events, total = AuditRepository(session).list_for_complaint(complaint_id)

    assert total == 2
    assert [e.event_type for e in events] == [
        AuditEventType.COMPLAINT_CREATED,
        AuditEventType.COMPLAINT_CLASSIFIED,
    ]
    assert events[1].evidence[0]["doc_id"] == "KB-RULE-STREETLIGHT-01"
    assert events[1].occurred_at > events[0].occurred_at


def test_audit_repository_has_no_update_or_delete() -> None:
    public = {name for name in dir(AuditRepository) if not name.startswith("_")}

    assert public == {"append", "list_for_complaint"}


def test_service_create_records_complaint_and_audit_in_one_unit(
    database: Database, clock: FixedClock
) -> None:
    with database.session() as session:
        complaint = ComplaintService(session, clock).create(
            ComplaintCreateRequest(citizen_input="Garbage not collected for a week", language="en")
        )
        complaint_id = complaint.id

    with database.session() as session:
        events = session.query(AuditEvent).filter_by(complaint_id=complaint_id).all()

    assert len(events) == 1
    assert events[0].event_type is AuditEventType.COMPLAINT_CREATED
    # The audit payload records metadata, not the citizen's text.
    assert "Garbage" not in str(events[0].payload)
