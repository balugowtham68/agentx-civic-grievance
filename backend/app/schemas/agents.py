"""Input/output contracts for the five agents.

These are the stable interfaces between the orchestrator, the agents and the
frontend. Phases 2-8 implement the behaviour; they must not change these shapes
without documenting a breaking change.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.schemas.complaint import LANGUAGE_CODE_PATTERN, SLAStateRead
from app.schemas.enums import (
    AuthorityStatus,
    ComplaintStatus,
    EscalationState,
    InputChannel,
    SLAStage,
)

# --------------------------------------------------------------------------
# Agent 1 - Citizen Intake
# --------------------------------------------------------------------------


class ExtractedField(BaseModel):
    """A fact extracted from the citizen's words.

    `source_span` must quote the citizen. A field with no quote stays None and
    is reported as missing - it is never guessed.
    """

    value: str
    source_span: str


class ExtractedEntity(BaseModel):
    type: str  # e.g. "landmark", "pole_number", "street"
    value: str
    source_span: str


class ExtractedGrievance(BaseModel):
    issue: ExtractedField | None = None
    location: ExtractedField | None = None
    duration: ExtractedField | None = None
    entities: list[ExtractedEntity] = Field(default_factory=list)


class IntakeRequest(BaseModel):
    complaint_id: str
    channel: InputChannel = InputChannel.TEXT
    text: str | None = Field(default=None, max_length=2000)
    audio_ref: str | None = None  # uploaded audio reference for transcription
    language_hint: str | None = Field(default=None, pattern=LANGUAGE_CODE_PATTERN)


class IntakeResponse(BaseModel):
    complaint_id: str
    detected_language: str
    transcript: str
    translated_text: str  # working-language (English) version
    extracted: ExtractedGrievance
    missing_fields: list[str] = Field(default_factory=list)
    follow_up_question: str | None = None  # in the citizen's language
    status: Literal[ComplaintStatus.UNDERSTOOD, ComplaintStatus.NEEDS_INFO]


# --------------------------------------------------------------------------
# Agent 2 - Classification & Reasoning
# --------------------------------------------------------------------------


class Evidence(BaseModel):
    doc_id: str
    snippet: str
    score: float | None = None


class ClassificationRequest(BaseModel):
    complaint_id: str
    translated_text: str
    extracted: ExtractedGrievance


class ClassificationResponse(BaseModel):
    complaint_id: str
    category: str | None
    department_id: str | None
    jurisdiction_id: str | None
    sla_policy_id: str | None
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: list[Evidence] = Field(default_factory=list)
    reasoning: str
    missing_for_category: list[str] = Field(default_factory=list)
    status: Literal[
        ComplaintStatus.CLASSIFIED, ComplaintStatus.NEEDS_INFO, ComplaintStatus.NEEDS_REVIEW
    ]


# --------------------------------------------------------------------------
# Agent 3 - Complaint Drafting
# --------------------------------------------------------------------------


class DraftedComplaint(BaseModel):
    issue: str
    category: str
    department_id: str
    jurisdiction_id: str
    location: str
    duration: str | None = None
    description: str
    requested_action: str
    supporting_details: list[str] = Field(default_factory=list)
    original_text: str  # citizen's own words, always attached


class DraftRequest(BaseModel):
    complaint_id: str
    intake: IntakeResponse
    classification: ClassificationResponse


class DraftResponse(BaseModel):
    complaint_id: str
    draft: DraftedComplaint
    citizen_summary: str  # plain-language summary for review before filing
    summary_language: str


# --------------------------------------------------------------------------
# Agent 4 - Filing (Mock Government Grievance API only)
# --------------------------------------------------------------------------


class FilingRequest(BaseModel):
    complaint_id: str
    draft: DraftedComplaint
    citizen_confirmed: bool

    @field_validator("citizen_confirmed")
    @classmethod
    def _must_be_confirmed(cls, value: bool) -> bool:
        if not value:
            raise ValueError("A complaint cannot be filed without citizen confirmation")
        return value


class FilingResponse(BaseModel):
    complaint_id: str
    tracking_id: str  # only ever taken from the mock API response
    received_at: datetime
    simulation: Literal[True] = True
    sla: SLAStateRead
    status: Literal[ComplaintStatus.MONITORING, ComplaintStatus.FILING_FAILED]


# --------------------------------------------------------------------------
# Agent 5 - Autonomous Watchdog
# --------------------------------------------------------------------------


class ConditionResult(BaseModel):
    name: str
    expected: str
    actual: str
    passed: bool


class RuleEvaluation(BaseModel):
    policy_id: str
    level: int
    matched: bool
    conditions: list[ConditionResult]
    evaluated_at: datetime


class EscalationResult(BaseModel):
    complaint_id: str
    policy_id: str
    level: int
    target_authority_id: str
    state: EscalationState
    reason: str  # rendered from the RuleEvaluation that fired
    mock_reference: str | None = None
    created: bool  # False when an existing escalation was returned (idempotent)


class WatchdogEvaluationRequest(BaseModel):
    complaint_id: str
    evaluated_at: datetime


class WatchdogEvaluationResult(BaseModel):
    complaint_id: str
    evaluated_at: datetime
    previous_status: ComplaintStatus
    new_status: ComplaintStatus
    authority_status: AuthorityStatus
    sla_stage: SLAStage
    warning_raised: bool = False
    rule_evaluations: list[RuleEvaluation] = Field(default_factory=list)
    escalation: EscalationResult | None = None
    reasons: list[str] = Field(default_factory=list)
