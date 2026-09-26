"""Classification state for a complaint (Phase 3).

One row per complaint, in the existing database (no second complaint store).
Queryable columns hold the decision; `result` holds the full ClassificationResult
snapshot (evidence, retrieved source references, rule matches, reasoning).
The complaint row receives category / department_id / jurisdiction_id only when
the complaint is CLASSIFIED.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, UTCDateTime, enum_column
from app.schemas.classification import ClassificationStatus, ConfidenceState
from app.schemas.intake import ProcessingMode


class ClassificationRecord(Base):
    __tablename__ = "classification_records"

    complaint_id: Mapped[str] = mapped_column(ForeignKey("complaints.id", ondelete="CASCADE"), primary_key=True)
    classification_status: Mapped[ClassificationStatus] = mapped_column(enum_column(ClassificationStatus), index=True)
    confidence_state: Mapped[ConfidenceState] = mapped_column(enum_column(ConfidenceState))
    category: Mapped[str | None] = mapped_column(String(64))
    department_id: Mapped[str | None] = mapped_column(String(64))
    jurisdiction_id: Mapped[str | None] = mapped_column(String(64))
    processing_mode: Mapped[ProcessingMode] = mapped_column(enum_column(ProcessingMode))
    missing_information: Mapped[list[str]] = mapped_column(JSON, default=list)
    source_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    # Citizen answers to Phase 3 questions, in order (citizen evidence).
    answers: Mapped[list[dict[str, object]]] = mapped_column(JSON, default=list)
    knowledge_base_version: Mapped[str | None] = mapped_column(String(64))
    result: Mapped[dict[str, object]] = mapped_column(JSON)
    runs: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime())
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime())
