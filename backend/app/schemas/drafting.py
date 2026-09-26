"""Phase 4 - Complaint Drafting contracts.

The drafting agent works from a fact-locked `DraftFactSet` built from the
confirmed Phase 2 handoff and the Phase 3 classification result. Every sentence
of a draft is either template wording (no facts) or a fact from that set.
Category, department and jurisdiction are copied from Phase 3 and cannot be
changed by drafting, by the optional AI, or by a citizen edit.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.security import sanitize_text
from app.schemas.enums import ComplaintStatus
from app.schemas.intake import ProcessingMode, ProviderTraceStep

DRAFT_EDIT_MAX_CHARS = 1500


class DraftValidationStatus(StrEnum):
    VALID = "VALID"  # generated (template or accepted AI wording) and every check passed
    FALLBACK_USED = "FALLBACK_USED"  # the optional AI wording was rejected or failed; template draft used
    NEEDS_REVIEW = "NEEDS_REVIEW"  # a citizen edit adds information that is not in the confirmed facts (kept, unverified)
    INVALID = "INVALID"  # never stored as the current draft


class DraftOrigin(StrEnum):
    GENERATED = "generated"
    CITIZEN_EDIT = "citizen_edit"


class ReviewStatus(StrEnum):
    PENDING_REVIEW = "PENDING_REVIEW"
    APPROVED = "APPROVED"  # the citizen approved this version (complaint DRAFTED)
    SUPERSEDED = "SUPERSEDED"  # was approved, then the citizen edited the draft; this version is kept unchanged


# ------------------------------------------------------------------ fact set


class LockedFact(BaseModel):
    """A citizen-provided fact: the (English) value and the citizen's own words."""

    value: str
    citizen_words: str
    source: str  # citizen_statement | citizen_correction | citizen_clarification


class DraftFactSet(BaseModel):
    """The only source of truth a draft may use."""

    complaint_id: str
    original_text: str
    citizen_language: str
    issue: LockedFact
    location: LockedFact
    location_answers: list[LockedFact] = Field(default_factory=list)
    category_answers: list[LockedFact] = Field(default_factory=list)  # citizen's answers to a Phase 3 category question
    duration: LockedFact | None = None
    identifiers: list[LockedFact] = Field(default_factory=list)
    category: str
    category_record_id: str
    category_name: str  # English display name from the knowledge base
    department_id: str
    department_name: str
    jurisdiction_id: str | None
    jurisdiction_name: str | None
    resolved_place: str | None  # configured locality/landmark matched by Phase 3
    location_precision: str
    source_ids: list[str]
    classification_explanation: str
    service_guideline: str | None = None
    safety_flags: list[str] = Field(default_factory=list)
    demo_data: bool = True

    def citizen_texts(self) -> list[str]:
        texts = [self.original_text, self.issue.citizen_words, self.issue.value, self.location.citizen_words,
                 self.location.value]
        texts += [a.citizen_words for a in self.location_answers]
        texts += [a.citizen_words for a in self.category_answers]
        if self.duration:
            texts += [self.duration.citizen_words, self.duration.value]
        texts += [i.citizen_words for i in self.identifiers] + [i.value for i in self.identifiers]
        return texts

    def locked_texts(self) -> list[str]:
        """Citizen facts plus the Phase 3 names the draft may mention."""
        names = [self.category, self.category_name, self.department_id, self.department_name]
        names += [n for n in (self.jurisdiction_id, self.jurisdiction_name, self.resolved_place) if n]
        return self.citizen_texts() + names


# ------------------------------------------------------------------ draft


class DraftSections(BaseModel):
    """The editable wording of a draft. The body is composed from these sections."""

    subject: str
    summary: str
    issue_text: str
    location_text: str
    duration_text: str
    requested_action: str


class EvidenceReference(BaseModel):
    kind: Literal["citizen", "classification", "knowledge"]
    field: str
    text: str
    source: str


class ComplaintDraft(BaseModel):
    draft_id: str
    complaint_id: str
    version: int
    origin: DraftOrigin
    based_on_version: int | None = None
    sections: DraftSections
    body: str
    # Locked structured metadata (from Phase 3; never editable here).
    category: str
    category_name: str
    department_id: str
    department_name: str
    jurisdiction_id: str | None
    jurisdiction_name: str | None
    location: dict[str, str | None]  # citizen words, resolved place, precision - kept distinct
    duration: str | None
    chronology: list[str] = Field(default_factory=list)
    supporting_facts: list[str] = Field(default_factory=list)
    evidence_references: list[EvidenceReference] = Field(default_factory=list)
    source_ids: list[str] = Field(default_factory=list)
    citizen_statement: str | None  # verbatim original, omitted from the body when flagged unsafe
    citizen_language: str
    draft_language: str
    language_note: str | None = None
    processing_mode: ProcessingMode
    validation_status: DraftValidationStatus
    validation_issues: list[str] = Field(default_factory=list)
    # Citizen edits: information the citizen added that is NOT verified system evidence.
    citizen_added_information: list[str] = Field(default_factory=list)
    review_status: ReviewStatus
    explanation: str
    ai_generated_notice: str = "AI-generated draft — please review before filing."
    generated_at: datetime
    created_by: Literal["agent", "citizen"]
    demo_data: bool = True


class DraftSummary(BaseModel):
    version: int
    origin: DraftOrigin
    validation_status: DraftValidationStatus
    review_status: ReviewStatus
    subject: str
    generated_at: datetime
    created_by: str


class DraftView(BaseModel):
    """GET /drafting/{id}: the current version plus the version history."""

    complaint_id: str
    status: ComplaintStatus
    current: ComplaintDraft
    versions: list[DraftSummary]
    approved_version: int | None = None  # the version the citizen approved (complaint DRAFTED), if any


# ------------------------------------------------------------------ agent contract


class DraftingRequest(BaseModel):
    facts: DraftFactSet
    draft_language: str = "en"
    draft_id: str
    version: int = 1


class DraftingResult(BaseModel):
    draft: ComplaintDraft
    provider_trace: list[ProviderTraceStep] = Field(default_factory=list)
    rejected_ai_output: list[str] = Field(default_factory=list)


# ------------------------------------------------------------------ API requests


class DraftRunRequest(BaseModel):
    draft_language: str = Field(default="en", pattern=r"^[a-z]{2,3}$")


class DraftEditRequest(BaseModel):
    """Citizen edits of the wording. Category, department and jurisdiction are not editable."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    based_on_version: int = Field(ge=1)
    subject: str | None = Field(default=None, max_length=200)
    summary: str | None = Field(default=None, max_length=DRAFT_EDIT_MAX_CHARS)
    issue_text: str | None = Field(default=None, max_length=DRAFT_EDIT_MAX_CHARS)
    location_text: str | None = Field(default=None, max_length=DRAFT_EDIT_MAX_CHARS)
    duration_text: str | None = Field(default=None, max_length=DRAFT_EDIT_MAX_CHARS)
    requested_action: str | None = Field(default=None, max_length=DRAFT_EDIT_MAX_CHARS)

    @field_validator("subject", "summary", "issue_text", "location_text", "duration_text", "requested_action")
    @classmethod
    def _clean(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = sanitize_text(value)
        if not cleaned:
            raise ValueError("must not be empty after removing markup")
        return cleaned

    @model_validator(mode="after")
    def _something_changed(self) -> "DraftEditRequest":
        if all(getattr(self, f) is None for f in DraftSections.model_fields):
            raise ValueError("Provide at least one field to edit")
        return self


class DraftApproveRequest(BaseModel):
    version: int = Field(ge=1)
