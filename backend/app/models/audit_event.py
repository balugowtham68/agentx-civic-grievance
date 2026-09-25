"""Append-only audit log."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, UTCDateTime
from app.database.base import enum_column as _enum
from app.schemas.enums import ActorType, AuditEventType


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # Nullable for system-level events not tied to one complaint.
    complaint_id: Mapped[str | None] = mapped_column(
        ForeignKey("complaints.id", ondelete="CASCADE"), index=True
    )
    event_type: Mapped[AuditEventType] = mapped_column(_enum(AuditEventType), index=True)
    actor_type: Mapped[ActorType] = mapped_column(_enum(ActorType))
    actor_name: Mapped[str] = mapped_column(String(64))
    summary: Mapped[str] = mapped_column(String(500))
    payload: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    evidence: Mapped[list[dict[str, object]]] = mapped_column(JSON, default=list)
    occurred_at: Mapped[datetime] = mapped_column(UTCDateTime(), index=True)
    # Simulated time at the moment of the event (Phase 7 accelerated clock).
    sim_time: Mapped[datetime | None] = mapped_column(UTCDateTime())
