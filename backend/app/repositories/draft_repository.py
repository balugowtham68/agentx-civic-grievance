"""Persistence for complaint draft versions. No business rules here."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.draft import DraftRecord


class DraftRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def versions(self, complaint_id: str) -> list[DraftRecord]:
        stmt = select(DraftRecord).where(DraftRecord.complaint_id == complaint_id).order_by(DraftRecord.version)
        return list(self.session.scalars(stmt))

    def latest(self, complaint_id: str) -> DraftRecord | None:
        versions = self.versions(complaint_id)
        return versions[-1] if versions else None

    def get_version(self, complaint_id: str, version: int) -> DraftRecord | None:
        stmt = select(DraftRecord).where(DraftRecord.complaint_id == complaint_id, DraftRecord.version == version)
        return self.session.scalars(stmt).first()

    def add(self, record: DraftRecord) -> DraftRecord:
        self.session.add(record)
        self.session.flush()
        return record
