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


class ComplaintSubmitRequest(BaseModel):
    """Fast-acknowledgement citizen grievance intake with mandatory GPS and photo proof."""

    model_config = ConfigDict(str_strip_whitespace=True)

    text: str = Field(min_length=1, max_length=2000, description="Citizen's grievance statement")
    language: str | None = Field(default=None, description="ISO language hint, e.g. 'te'")
    channel: InputChannel = InputChannel.TEXT
    location: str | None = Field(default=None, description="Area, landmark, or street name")
    latitude: float | None = Field(default=None, description="Mandatory GPS latitude")
    longitude: float | None = Field(default=None, description="Mandatory GPS longitude")
    photo_data: str | None = Field(default=None, description="Mandatory photo proof as base64 data URL")
    confirmed_category: str | None = Field(default=None, description="Citizen-confirmed problem category")
    confirmed_department: str | None = Field(default=None, description="Citizen-confirmed department ID")
    draft_subject: str | None = Field(default=None, description="Citizen-confirmed grievance draft subject")
    draft_body: str | None = Field(default=None, description="Citizen-confirmed grievance draft body")


class ProblemOption(BaseModel):
    id: str
    category: str
    label: str
    label_local: str | None = None
    department_id: str
    department_name: str
    description: str
    sla_hours: int
    db_count: int = 0


class PostgresMatch(BaseModel):
    tracking_id: str
    issue: str
    category: str | None = None
    status: str
    location: str | None = None


class GeneratedDraft(BaseModel):
    subject: str
    subject_local: str
    body: str
    department_id: str
    department_name: str
    jurisdiction: str
    sla_hours: int
    urgency: str = "HIGH"


class ProblemDetectRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2000)
    language: str | None = "en"
    latitude: float | None = None
    longitude: float | None = None
    photo_data: str | None = None
    location: str | None = None


class ProblemDetectResponse(BaseModel):
    detected_problem: ProblemOption
    related_options: list[ProblemOption]
    postgres_matches: list[PostgresMatch]
    draft: GeneratedDraft
    location_summary: str
    coordinates: dict[str, float] | None = None
    has_photo_proof: bool = True
    total_db_complaints: int = 0


class FastAckResponse(BaseModel):
    """Immediate acknowledgement returned to the citizen in < 500ms."""

    complaint_id: str
    tracking_id: str
    status: str = "RECEIVED"
    message: str = "Your complaint has been received. SPANDAN AI is processing it in the background."
    created_at: datetime
    has_photo_proof: bool = True
    location_summary: str | None = None


class TimelineStage(BaseModel):
    stage: str
    label: str
    description: str
    timestamp: datetime | None = None
    status: str  # COMPLETED, IN_PROGRESS, PENDING


class TimelineResponse(BaseModel):
    complaint_id: str
    tracking_id: str
    current_status: ComplaintStatus
    stages: list[TimelineStage]
    department: str | None = None
    jurisdiction: str | None = None
    location: str | None = None
    issue: str | None = None
    sla_deadline: datetime | None = None
    photo_url: str | None = None
    has_photo_proof: bool = False
    gps_coordinates: dict[str, float] | None = None


