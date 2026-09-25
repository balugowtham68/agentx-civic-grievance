"""Audit event contracts. Audit records are append-only."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.enums import ActorType, AuditEventType


class AuditEventCreate(BaseModel):
    complaint_id: str | None = None
    event_type: AuditEventType
    actor_type: ActorType
    actor_name: str = Field(min_length=1, max_length=64)
    summary: str = Field(min_length=1, max_length=500)
    payload: dict[str, object] = Field(default_factory=dict)
    # Evidence behind a decision (KB doc ids, rule conditions, API receipts).
    # Explanations in Phase 9 are rendered from this, never generated afterwards.
    evidence: list[dict[str, object]] = Field(default_factory=list)
    sim_time: datetime | None = None


class AuditEventRead(AuditEventCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    occurred_at: datetime


class AuditEventListResponse(BaseModel):
    items: list[AuditEventRead]
    total: int
