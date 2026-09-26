"""Complaint orchestration entry points used by the API layer.

Phase 1 scope: record a raw complaint (status CREATED) with its audit event,
and read complaints back. Intake, classification, drafting and filing are wired
in by the orchestrator in Phases 2-5.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.clock import Clock, get_clock
from app.core.errors import NotFoundError
from app.models import Complaint
from app.repositories import ComplaintRepository
from app.schemas.audit import AuditEventCreate
from app.schemas.complaint import (
    ComplaintCreateRequest,
    ComplaintStatusResponse,
    EscalationRead,
    SLAStateRead,
)
from app.schemas.enums import (
    ActorType,
    AuditEventType,
    AuthorityStatus,
    ComplaintStatus,
)
from app.services.audit_service import AuditService


class ComplaintService:
    def __init__(self, session: Session, clock: Clock | None = None) -> None:
        self.clock = clock or get_clock()
        self.repo = ComplaintRepository(session)
        self.audit = AuditService(session, self.clock)

    def create(self, request: ComplaintCreateRequest, *, complaint_id: str | None = None) -> Complaint:
        now = self.clock.now()
        complaint = self.repo.add(
            Complaint(
                **({"id": complaint_id} if complaint_id else {}),
                citizen_input=request.citizen_input,
                input_channel=request.channel,
                language=request.language,
                status=ComplaintStatus.CREATED,
                authority_status=AuthorityStatus.NONE,
                created_at=now,
                updated_at=now,
            )
        )
        self.audit.record(
            AuditEventCreate(
                complaint_id=complaint.id,
                event_type=AuditEventType.COMPLAINT_CREATED,
                actor_type=ActorType.CITIZEN,
                actor_name="citizen",
                summary="Citizen submitted a grievance",
                # Store length and channel, not the text itself: the text is on the complaint.
                payload={
                    "channel": request.channel.value,
                    "language_hint": request.language,
                    "characters": len(request.citizen_input),
                },
            )
        )
        return complaint

    def get(self, complaint_id: str) -> Complaint:
        complaint = self.repo.get(complaint_id)
        if complaint is None:
            raise NotFoundError(f"Complaint {complaint_id!r} not found")
        return complaint

    def get_by_tracking_id(self, tracking_id: str) -> Complaint:
        complaint = self.repo.get_by_tracking_id(tracking_id)
        if complaint is None:
            raise NotFoundError(f"No complaint with tracking ID {tracking_id!r}")
        return complaint

    def list(
        self, *, statuses: set[ComplaintStatus] | None = None, limit: int = 50, offset: int = 0
    ) -> tuple[list[Complaint], int]:
        return self.repo.list(statuses=statuses, limit=limit, offset=offset)

    def status(self, complaint_id: str) -> ComplaintStatusResponse:
        complaint = self.get(complaint_id)
        return ComplaintStatusResponse(
            id=complaint.id,
            tracking_id=complaint.tracking_id,
            status=complaint.status,
            authority_status=complaint.authority_status,
            sla=SLAStateRead.model_validate(complaint.sla) if complaint.sla else None,
            escalation_state=complaint.escalation_state,
            escalations=[EscalationRead.model_validate(e) for e in complaint.escalations],
            updated_at=complaint.updated_at,
        )
