"""Input/output contracts for the five agents.

These are the stable interfaces between the orchestrator, the agents and the
frontend. Phases 2-8 implement the behaviour; they must not change these shapes
without documenting a breaking change.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.schemas.classification import (  # noqa: F401 - re-exported
    ClassificationRequest,
    ClassificationResult,
)
from app.schemas.complaint import SLAStateRead
from app.schemas.drafting import (  # noqa: F401 - re-exported
    DraftingRequest,
    DraftingResult,
)
from app.schemas.enums import (
    AuthorityStatus,
    ComplaintStatus,
    EscalationState,
    SLAStage,
)
from app.schemas.intake import (  # noqa: F401 - re-exported Phase 1 names
    ExtractedEntity,
    ExtractedField,
    ExtractedGrievance,
    IntakeRequest,
    IntakeResponse,
    IntakeResult,
)

# --------------------------------------------------------------------------
# Agent 1 - Citizen Intake: contracts live in app/schemas/intake.py (Phase 2).
# Re-exported here so Phase 1 imports keep working.
# --------------------------------------------------------------------------

# --------------------------------------------------------------------------
# Agent 2 - Classification & Reasoning
# --------------------------------------------------------------------------


# Contracts live in app/schemas/classification.py (Phase 3). The Phase 1 stub
# (numeric confidence, NEEDS_REVIEW-only outcomes) was replaced: SPANDAN AI does not
# emit fake confidence scores, and outcomes are CLASSIFIED / NEEDS_INFO / AMBIGUOUS /
# UNSUPPORTED_CLASSIFICATION with a controlled confidence_state.
ClassificationResponse = ClassificationResult


# --------------------------------------------------------------------------
# Agent 3 - Complaint Drafting
# --------------------------------------------------------------------------


class DraftedComplaint(BaseModel):
    """The citizen-approved draft as the Filing Agent (Phase 5) will consume it."""

    issue: str
    category: str
    department_id: str
    jurisdiction_id: str | None  # None only for categories that do not require one (none in the demo KB)
    location: str
    duration: str | None = None
    description: str
    requested_action: str
    supporting_details: list[str] = Field(default_factory=list)
    original_text: str  # citizen's own words, always attached
    # Phase 4 additions (optional, so earlier callers keep working).
    subject: str | None = None
    body: str | None = None
    draft_id: str | None = None
    draft_version: int | None = None


# Phase 4 contracts live in app/schemas/drafting.py (DraftingRequest -> DraftingResult).
# DraftedComplaint above stays the Phase 5 filing payload; the drafting service fills it
# from the citizen-approved draft.
DraftRequest = DraftingRequest
DraftResponse = DraftingResult


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
