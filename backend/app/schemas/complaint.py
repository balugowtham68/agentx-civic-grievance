"""Complaint, SLA and escalation API contracts."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.security import sanitize_text
from app.schemas.enums import (
    AuthorityStatus,
    ComplaintStatus,
    EscalationState,
    InputChannel,
    SLAStage,
)

LANGUAGE_CODE_PATTERN = r"^[a-z]{2,3}(-[A-Z]{2})?$"


class ComplaintCreateRequest(BaseModel):
    """Raw citizen grievance as received. Phase 2 enriches it via the Intake Agent."""

    model_config = ConfigDict(str_strip_whitespace=True)

    citizen_input: str = Field(min_length=3, max_length=2000, description="Citizen's own words")
    language: str | None = Field(
        default=None, pattern=LANGUAGE_CODE_PATTERN, description="ISO code hint, e.g. 'te'"
    )
    channel: InputChannel = InputChannel.TEXT

    @field_validator("citizen_input")
    @classmethod
    def _sanitise(cls, value: str) -> str:
        cleaned = sanitize_text(value)
        if len(cleaned) < 3:
            raise ValueError("Complaint text is empty after removing markup")
        return cleaned


class SLAStateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    policy_id: str
    started_at: datetime
    warning_at: datetime
    deadline_at: datetime
    stage: SLAStage
    stopped_at: datetime | None = None
    stop_reason: str | None = None


class EscalationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    level: int
    policy_id: str
    target_authority_id: str
    state: EscalationState
    reason: str
    mock_reference: str | None = None
    created_at: datetime
    updated_at: datetime


class ComplaintRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    tracking_id: str | None
    citizen_input: str
    input_channel: InputChannel
    language: str | None
    issue: str | None
    location: str | None
    duration: str | None
    category: str | None
    department_id: str | None
    jurisdiction_id: str | None
    drafted_complaint: dict[str, object] | None
    status: ComplaintStatus
    authority_status: AuthorityStatus
    sla_start: datetime | None
    sla_deadline: datetime | None
    escalation_state: EscalationState
    created_at: datetime
    updated_at: datetime


class ComplaintSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    tracking_id: str | None
    issue: str | None
    status: ComplaintStatus
    authority_status: AuthorityStatus
    escalation_state: EscalationState
    created_at: datetime
    updated_at: datetime


class ComplaintListResponse(BaseModel):
    items: list[ComplaintSummary]
    total: int


class ComplaintStatusResponse(BaseModel):
    """What the citizen tracking view needs in one call."""

    id: str
    tracking_id: str | None
    status: ComplaintStatus
    authority_status: AuthorityStatus
    sla: SLAStateRead | None
    escalation_state: EscalationState
    escalations: list[EscalationRead]
    updated_at: datetime
