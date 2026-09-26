"""Phase 3 - Classification & Reasoning contracts.

The civic knowledge base (knowledge_base/) and its configured rules are the
source of truth. Retrieval proposes candidates, configured rules and the
citizen's own words validate them, and an optional AI can only choose among
validated candidates. There are no numeric confidence scores: the outcome is a
controlled state (SUPPORTED, PARTIALLY_SUPPORTED, AMBIGUOUS, UNSUPPORTED).
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.enums import ComplaintStatus
from app.schemas.intake import (
    ClarificationQuestion,
    IntakeHandoff,
    ProcessingMode,
    ProviderTraceStep,
)


class ClassificationStatus(StrEnum):
    CLASSIFIED = "CLASSIFIED"
    NEEDS_INFO = "NEEDS_INFO"
    AMBIGUOUS = "AMBIGUOUS"
    UNSUPPORTED_CLASSIFICATION = "UNSUPPORTED_CLASSIFICATION"


class ConfidenceState(StrEnum):
    """How well the decision is supported. Not a probability."""

    SUPPORTED = "SUPPORTED"  # configured rule matched the citizen's words AND retrieval agreed
    PARTIALLY_SUPPORTED = "PARTIALLY_SUPPORTED"  # one of them only, or chosen by the optional AI
    AMBIGUOUS = "AMBIGUOUS"
    UNSUPPORTED = "UNSUPPORTED"


class LocationPrecision(StrEnum):
    EXACT = "EXACT"  # a configured locality, a named street/place, or an address with a number
    LANDMARK = "LANDMARK"  # "near <named place>"
    VAGUE = "VAGUE"  # "our street", "near my house"
    MISSING = "MISSING"


class JurisdictionStatus(StrEnum):
    RESOLVED = "RESOLVED"  # matched a configured jurisdiction from the citizen's words
    UNRESOLVED = "UNRESOLVED"  # nothing matched yet; the citizen is asked
    AMBIGUOUS = "AMBIGUOUS"  # words match more than one configured jurisdiction
    UNSUPPORTED = "UNSUPPORTED"  # the citizen named a place outside the configured area
    NOT_REQUIRED = "NOT_REQUIRED"


class RetrievedKnowledge(BaseModel):
    """One retrieved knowledge-base chunk, with provenance."""

    doc_id: str
    source_id: str
    source_name: str
    source_type: str
    source_version: str
    official: bool
    record_type: str  # category | guideline | department | jurisdiction | timeline
    record_id: str
    category: str | None = None
    department_id: str | None = None
    language: str | None = None
    content: str
    similarity: float = Field(description="Cosine similarity of the local embedding. A retrieval score, not a confidence.")


class RuleMatch(BaseModel):
    """A configured phrase from the knowledge base found in the citizen's own words."""

    rule_id: str  # category record id, ambiguity group id or jurisdiction id
    rule_type: Literal["category_pattern", "ambiguity_term", "jurisdiction_place", "suppression"]
    category: str | None = None
    pattern: str
    language: str
    citizen_words: str  # exact slice of the citizen's text
    source: Literal["original_text", "issue", "location", "answer", "correction"]


class Candidate(BaseModel):
    category: str
    record_id: str
    display_name: str
    retrieved: bool
    best_similarity: float | None = None
    rule_matched: bool
    decision: Literal["selected", "rejected", "suppressed", "ambiguous", "suggested"]
    reason: str


class ClassificationEvidence(BaseModel):
    kind: Literal["citizen", "knowledge"]
    field: str  # issue | location | category | department | jurisdiction | guideline
    text: str
    source: str  # citizen_statement | citizen_correction | citizen_clarification | <record id>


class DepartmentAssignment(BaseModel):
    department_id: str
    name: str
    source_id: str
    mapping_record_id: str  # the category record that configures this mapping
    label: str = "DEMO CIVIC RULE"


class JurisdictionResult(BaseModel):
    status: JurisdictionStatus
    jurisdiction_id: str | None = None
    name: str | None = None
    matched_place: str | None = None
    matched_words: str | None = None
    source_id: str | None = None
    location_precision: LocationPrecision
    note: str | None = None


class RequiredInformation(BaseModel):
    field: str
    requirement: Literal["REQUIRED", "OPTIONAL"]
    present: bool
    detail: str | None = None


class ReasoningStep(BaseModel):
    step: Literal[
        "citizen_evidence", "retrieval", "rule_validation", "ai_reasoning", "department_mapping",
        "jurisdiction", "required_information", "decision",
    ]
    detail: str
    source_ids: list[str] = Field(default_factory=list)


class ServiceTimelineRef(BaseModel):
    """Reference data only. Phase 3 does not start or monitor any SLA."""

    policy_id: str
    duration_hours: int
    note: str = "Reference data for later phases; no SLA is started in Phase 3."


class ClassificationAnswer(BaseModel):
    """A citizen's answer to a Phase 3 clarification question (citizen evidence)."""

    text: str
    asked_for: Literal["locality", "category"]
    recorded_at: datetime


class ClassificationRequest(BaseModel):
    """What the Classification Agent receives: the confirmed Phase 2 handoff plus any
    answers the citizen gave to Phase 3 questions."""

    handoff: IntakeHandoff
    answers: list[ClassificationAnswer] = Field(default_factory=list)
    safety_flags: list[str] = Field(default_factory=list)


class ClassificationResult(BaseModel):
    complaint_id: str
    status: ComplaintStatus  # complaint status after this run
    classification_status: ClassificationStatus
    confidence_state: ConfidenceState
    category: str | None = None
    category_record_id: str | None = None
    category_name: str | None = None
    responsible_department: DepartmentAssignment | None = None
    jurisdiction: JurisdictionResult
    required_information: list[RequiredInformation] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    clarification_questions: list[ClarificationQuestion] = Field(default_factory=list)
    candidates: list[Candidate] = Field(default_factory=list)
    rule_matches: list[RuleMatch] = Field(default_factory=list)
    retrieved_sources: list[RetrievedKnowledge] = Field(default_factory=list)
    evidence: list[ClassificationEvidence] = Field(default_factory=list)
    reasoning: list[ReasoningStep] = Field(default_factory=list)
    explanation: str
    service_guideline: str | None = None
    service_timeline: ServiceTimelineRef | None = None
    processing_mode: ProcessingMode
    provider_trace: list[ProviderTraceStep] = Field(default_factory=list)
    rejected_ai_output: list[str] = Field(default_factory=list)
    safety_flags: list[str] = Field(default_factory=list)
    language: str
    answers: list[ClassificationAnswer] = Field(default_factory=list)
    knowledge_base_version: str | None = None
    demo_data: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ClassificationEvidenceView(BaseModel):
    complaint_id: str
    classification_status: ClassificationStatus
    evidence: list[ClassificationEvidence]
    rule_matches: list[RuleMatch]
    retrieved_sources: list[RetrievedKnowledge]
    source_ids: list[str]


class ClassificationExplanation(BaseModel):
    complaint_id: str
    classification_status: ClassificationStatus
    explanation: str
    reasoning: list[ReasoningStep]
    source_ids: list[str]
    demo_data: bool


class KnowledgeBaseStatus(BaseModel):
    ready: bool
    collection: str
    records: int
    expected_records: int
    embedder: str
    fingerprint: str | None
    stale: bool
    problems: list[str] = Field(default_factory=list)
