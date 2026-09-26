"""Persistence for classification records. No business rules here."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.classification import ClassificationRecord


class ClassificationRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, complaint_id: str) -> ClassificationRecord | None:
        return self.session.get(ClassificationRecord, complaint_id)

    def save(self, record: ClassificationRecord) -> ClassificationRecord:
        self.session.add(record)
        self.session.flush()
        return record
