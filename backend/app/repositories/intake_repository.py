"""Persistence for intake records. No business rules here."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.intake import IntakeRecord


class IntakeRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, complaint_id: str) -> IntakeRecord | None:
        return self.session.get(IntakeRecord, complaint_id)

    def save(self, record: IntakeRecord) -> IntakeRecord:
        self.session.add(record)
        self.session.flush()
        return record
