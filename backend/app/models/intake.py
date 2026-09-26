"""Intake state for a complaint (Phase 2).

A separate table (one row per complaint) rather than new columns on
`complaints`, so existing Phase 1 databases gain it through create_all without
a migration. The complaint row keeps the citizen's original text untouched and
receives the extracted issue/location/duration/language.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, UTCDateTime, enum_column
from app.schemas.intake import ConfirmationStatus, IntakeStatus


class IntakeRecord(Base):
    __tablename__ = "intake_records"

    complaint_id: Mapped[str] = mapped_column(
        ForeignKey("complaints.id", ondelete="CASCADE"), primary_key=True
    )
    intake_status: Mapped[IntakeStatus] = mapped_column(enum_column(IntakeStatus))
    confirmation_status: Mapped[ConfirmationStatus] = mapped_column(enum_column(ConfirmationStatus))
    original_language: Mapped[str | None] = mapped_column(String(8))
    translated_text: Mapped[str | None] = mapped_column(Text)
    # Citizen inputs after the original statement, kept in order.
    clarifications: Mapped[list[dict[str, object]]] = mapped_column(JSON, default=list)
    corrections: Mapped[list[dict[str, object]]] = mapped_column(JSON, default=list)
    # Latest IntakeResult snapshot (facts with evidence, missing info, questions, metadata).
    result: Mapped[dict[str, object]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime())
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime())
