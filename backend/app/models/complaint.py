"""Complaint aggregate: the complaint, its SLA record and its escalations."""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import JSON, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, UTCDateTime
from app.database.base import enum_column as _enum
from app.schemas.enums import (
    AuthorityStatus,
    ComplaintStatus,
    EscalationState,
    InputChannel,
    SLAStage,
)


class Complaint(Base):
    __tablename__ = "complaints"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tracking_id: Mapped[str | None] = mapped_column(String(32), unique=True, index=True)

    citizen_input: Mapped[str] = mapped_column(Text)
    input_channel: Mapped[InputChannel] = mapped_column(_enum(InputChannel))
    language: Mapped[str | None] = mapped_column(String(8))

    # Filled by Intake (Phase 2) and Classification (Phase 3).
    issue: Mapped[str | None] = mapped_column(String(500))
    location: Mapped[str | None] = mapped_column(String(500))
    duration: Mapped[str | None] = mapped_column(String(100))
    category: Mapped[str | None] = mapped_column(String(64))
    department_id: Mapped[str | None] = mapped_column(String(64))
    jurisdiction_id: Mapped[str | None] = mapped_column(String(64))

    # Filled by Drafting (Phase 4).
    drafted_complaint: Mapped[dict[str, object] | None] = mapped_column(JSON)

    status: Mapped[ComplaintStatus] = mapped_column(
        _enum(ComplaintStatus), default=ComplaintStatus.CREATED, index=True
    )
    authority_status: Mapped[AuthorityStatus] = mapped_column(
        _enum(AuthorityStatus), default=AuthorityStatus.NONE
    )

    created_at: Mapped[datetime] = mapped_column(UTCDateTime())
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime())

    sla: Mapped[SLARecord | None] = relationship(
        back_populates="complaint", uselist=False, cascade="all, delete-orphan", lazy="selectin"
    )
    escalations: Mapped[list[EscalationRecord]] = relationship(
        back_populates="complaint",
        cascade="all, delete-orphan",
        order_by="EscalationRecord.level",
        lazy="selectin",
    )

    @property
    def sla_start(self) -> datetime | None:
        return self.sla.started_at if self.sla else None

    @property
    def sla_deadline(self) -> datetime | None:
        return self.sla.deadline_at if self.sla else None

    @property
    def escalation_state(self) -> EscalationState:
        if not self.escalations:
            return EscalationState.NONE
        return self.escalations[-1].state


class SLARecord(Base):
    """SLA state for one complaint. Created by the Filing Agent (Phase 5)."""

    __tablename__ = "sla_records"

    complaint_id: Mapped[str] = mapped_column(
        ForeignKey("complaints.id", ondelete="CASCADE"), primary_key=True
    )
    policy_id: Mapped[str] = mapped_column(String(64))
    started_at: Mapped[datetime] = mapped_column(UTCDateTime())
    warning_at: Mapped[datetime] = mapped_column(UTCDateTime())
    deadline_at: Mapped[datetime] = mapped_column(UTCDateTime())
    stage: Mapped[SLAStage] = mapped_column(_enum(SLAStage), default=SLAStage.ON_TRACK)
    stopped_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    stop_reason: Mapped[str | None] = mapped_column(String(200))

    complaint: Mapped[Complaint] = relationship(back_populates="sla")


class EscalationRecord(Base):
    """One escalation to a human authority. Unique per (complaint, level) so the
    watchdog can never escalate the same level twice."""

    __tablename__ = "escalations"
    __table_args__ = (UniqueConstraint("complaint_id", "level", name="uq_escalation_level"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    complaint_id: Mapped[str] = mapped_column(
        ForeignKey("complaints.id", ondelete="CASCADE"), index=True
    )
    level: Mapped[int] = mapped_column(Integer)
    policy_id: Mapped[str] = mapped_column(String(64))
    target_authority_id: Mapped[str] = mapped_column(String(64))
    state: Mapped[EscalationState] = mapped_column(
        _enum(EscalationState), default=EscalationState.ESCALATED
    )
    reason: Mapped[str] = mapped_column(Text)
    mock_reference: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime())
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime())

    complaint: Mapped[Complaint] = relationship(back_populates="escalations")
