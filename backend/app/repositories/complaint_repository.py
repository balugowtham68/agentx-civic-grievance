"""Persistence for the complaint aggregate. No business rules here."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Complaint, EscalationRecord, SLARecord
from app.schemas.enums import ComplaintStatus


class ComplaintRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, complaint: Complaint) -> Complaint:
        self.session.add(complaint)
        self.session.flush()
        return complaint

    def get(self, complaint_id: str) -> Complaint | None:
        return self.session.get(Complaint, complaint_id)

    def get_by_tracking_id(self, tracking_id: str) -> Complaint | None:
        return self.session.scalar(select(Complaint).where(Complaint.tracking_id == tracking_id))

    def list(
        self,
        *,
        statuses: set[ComplaintStatus] | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Complaint], int]:
        query = select(Complaint)
        count_query = select(func.count()).select_from(Complaint)
        if statuses:
            query = query.where(Complaint.status.in_(statuses))
            count_query = count_query.where(Complaint.status.in_(statuses))
        rows = self.session.scalars(
            query.order_by(Complaint.created_at.desc()).limit(limit).offset(offset)
        ).all()
        total = self.session.scalar(count_query) or 0
        return list(rows), total


class SLARepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, complaint_id: str) -> SLARecord | None:
        return self.session.get(SLARecord, complaint_id)

    def add(self, record: SLARecord) -> SLARecord:
        self.session.add(record)
        self.session.flush()
        return record


class EscalationRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_for_level(self, complaint_id: str, level: int) -> EscalationRecord | None:
        return self.session.scalar(
            select(EscalationRecord).where(
                EscalationRecord.complaint_id == complaint_id, EscalationRecord.level == level
            )
        )

    def list_for_complaint(self, complaint_id: str) -> list[EscalationRecord]:
        return list(
            self.session.scalars(
                select(EscalationRecord)
                .where(EscalationRecord.complaint_id == complaint_id)
                .order_by(EscalationRecord.level)
            ).all()
        )

    def add(self, record: EscalationRecord) -> EscalationRecord:
        """Raises IntegrityError if this level already exists (duplicate guard)."""
        self.session.add(record)
        self.session.flush()
        return record
