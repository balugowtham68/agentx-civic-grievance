"""Append-only audit persistence. There is deliberately no update or delete."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import AuditEvent
from app.schemas.audit import AuditEventCreate


class AuditRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def append(self, event: AuditEventCreate, *, occurred_at: datetime) -> AuditEvent:
        row = AuditEvent(**event.model_dump(), occurred_at=occurred_at)
        self.session.add(row)
        self.session.flush()
        return row

    def list_for_complaint(
        self, complaint_id: str, *, limit: int = 200, offset: int = 0
    ) -> tuple[list[AuditEvent], int]:
        rows = self.session.scalars(
            select(AuditEvent)
            .where(AuditEvent.complaint_id == complaint_id)
            .order_by(AuditEvent.id)
            .limit(limit)
            .offset(offset)
        ).all()
        total = self.session.scalar(
            select(func.count()).select_from(AuditEvent).where(AuditEvent.complaint_id == complaint_id)
        )
        return list(rows), total or 0
