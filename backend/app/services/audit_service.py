"""Audit recording. Every service/agent records events through this, never by
writing AuditEvent rows directly."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.clock import Clock, get_clock
from app.core.logging import get_logger
from app.models import AuditEvent
from app.repositories import AuditRepository
from app.schemas.audit import AuditEventCreate

logger = get_logger(__name__)


class AuditService:
    def __init__(self, session: Session, clock: Clock | None = None) -> None:
        self.repo = AuditRepository(session)
        self.clock = clock or get_clock()

    def record(self, event: AuditEventCreate) -> AuditEvent:
        row = self.repo.append(event, occurred_at=self.clock.now())
        logger.info(
            "audit event",
            extra={
                "event_type": event.event_type.value,
                "complaint_id": event.complaint_id,
                "actor": event.actor_name,
            },
        )
        return row

    def list_for_complaint(
        self, complaint_id: str, *, limit: int = 200, offset: int = 0
    ) -> tuple[list[AuditEvent], int]:
        return self.repo.list_for_complaint(complaint_id, limit=limit, offset=offset)
