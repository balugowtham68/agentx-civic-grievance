"""Complaint drafts (Phase 4): one row per version, in the existing database.

Versions are never overwritten: a citizen edit adds a new row (origin
citizen_edit) that points to the version it was based on. The complaint's
original text and the Phase 2/3 records are never modified by drafting.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, UTCDateTime, enum_column
from app.schemas.drafting import DraftOrigin, DraftValidationStatus, ReviewStatus
from app.schemas.intake import ProcessingMode


class DraftRecord(Base):
    __tablename__ = "complaint_drafts"
    __table_args__ = (UniqueConstraint("complaint_id", "version", name="uq_draft_version"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)  # draft_id
    complaint_id: Mapped[str] = mapped_column(ForeignKey("complaints.id", ondelete="CASCADE"), index=True)
    version: Mapped[int] = mapped_column(Integer)
    origin: Mapped[DraftOrigin] = mapped_column(enum_column(DraftOrigin))
    based_on_version: Mapped[int | None] = mapped_column(Integer)
    subject: Mapped[str] = mapped_column(String(300))
    body: Mapped[str] = mapped_column(Text)
    language: Mapped[str] = mapped_column(String(8))  # citizen language
    draft_language: Mapped[str] = mapped_column(String(8))
    processing_mode: Mapped[ProcessingMode] = mapped_column(enum_column(ProcessingMode))
    validation_status: Mapped[DraftValidationStatus] = mapped_column(enum_column(DraftValidationStatus))
    review_status: Mapped[ReviewStatus] = mapped_column(enum_column(ReviewStatus))
    source_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    # Full ComplaintDraft snapshot (structured fields, evidence references, validation issues).
    draft: Mapped[dict[str, object]] = mapped_column(JSON)
    # The locked DraftFactSet this version was built from (for traceability and later edits).
    facts: Mapped[dict[str, object]] = mapped_column(JSON)
    created_by: Mapped[str] = mapped_column(String(16))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime())
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime())
