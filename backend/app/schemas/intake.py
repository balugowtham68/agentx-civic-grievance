"""Citizen Intake contracts (Agent 1, Phase 2).

Extends the Phase 1 intake contract (ExtractedField, ExtractedEntity,
ExtractedGrievance, IntakeRequest, IntakeResponse). Phase 1 field names are kept:
`source_span` is the evidence for a fact, and `detected_language`,
`missing_fields`, `follow_up_question` and `translated_text` are still available
as computed fields.

Safety rules encoded here:
- every extracted fact carries the citizen's exact words as evidence (`source_span`)
- confidence is `None` unless a provider actually returned one
- the original citizen text is never replaced; translation is stored separately
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator, model_validator

from app.core.security import sanitize_text
from app.schemas.complaint import LANGUAGE_CODE_PATTERN
from app.schemas.enums import ComplaintStatus, InputChannel

MAX_TEXT_CHARS = 2000
MAX_ANSWER_CHARS = 1000
MAX_FACT_CHARS = 300


class IntakeField(StrEnum):
    ISSUE = "issue"
    LOCATION = "location"
    DURATION = "duration"


class FieldRequirement(StrEnum):
    REQUIRED_TO_CONTINUE = "REQUIRED_TO_CONTINUE"
    OPTIONAL = "OPTIONAL"
    UNKNOWN = "UNKNOWN"  # extraction could not run, so presence is unknown


class FactSource(StrEnum):
    CITIZEN_STATEMENT = "citizen_statement"  # extracted from what the citizen said
    CITIZEN_CORRECTION = "citizen_correction"  # typed/said by the citizen as a correction


class DetectionMethod(StrEnum):
    DECLARED = "declared"  # citizen chose the language
    SCRIPT = "script"  # deterministic Unicode-script detection
    HEURISTIC = "heuristic"  # deterministic marker words (English / romanised Indian languages)
    PROVIDER = "provider"  # optional AI provider
    DEFAULT = "default"  # nothing conclusive; English assumed only if English words were seen


class TranslationStatus(StrEnum):
    NOT_REQUIRED = "NOT_REQUIRED"
    TRANSLATED = "TRANSLATED"
    FAILED = "FAILED"
    UNAVAILABLE = "UNAVAILABLE"


class ExtractionStatus(StrEnum):
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    NOT_RUN = "NOT_RUN"


class ExtractionMethod(StrEnum):
    OFFLINE_RULES = "offline_rules"  # deterministic patterns + language lexicons (default)
    AI_PROVIDER = "ai_provider"  # optional enhancement, only for facts offline could not find
    MIXED = "mixed"
    RULE_BASED_FALLBACK = "rule_based_fallback"  # kept for stored Phase 2 drafts
    NONE = "none"


class ProcessingMode(StrEnum):
    """How the complaint was understood - shown to the citizen and in the audit."""

    OFFLINE_RULE = "OFFLINE_RULE"
    OFFLINE_LOCAL_MODEL = "OFFLINE_LOCAL_MODEL"  # a local model (e.g. local speech-to-text) was used, no network AI
    OPTIONAL_AI = "OPTIONAL_AI"  # every accepted fact came from the optional AI provider
    MIXED = "MIXED"  # offline facts plus AI-provided facts/translation


FactMethod = Literal["rule", "lexicon", "ai", "citizen"]
FactQuality = Literal["clear", "vague", "partial"]


class IntakeStatus(StrEnum):
    COMPLETED = "COMPLETED"  # enough to continue
    NEEDS_INFO = "NEEDS_INFO"  # a REQUIRED_TO_CONTINUE field is missing
    NEEDS_LANGUAGE = "NEEDS_LANGUAGE"  # language not detected/supported; citizen must choose
    FAILED = "FAILED"  # extraction failed; nothing invented; retry possible


class ConfirmationStatus(StrEnum):
    NOT_READY = "NOT_READY"  # required information still missing
    PENDING = "PENDING"  # waiting for the citizen to confirm "What I understood"
    CONFIRMED = "CONFIRMED"


class StatementKind(StrEnum):
    ORIGINAL = "original"
    CLARIFICATION = "clarification"


# --------------------------------------------------------------------------
# Facts (Phase 1 names kept)
# --------------------------------------------------------------------------


class ExtractedField(BaseModel):
    """A fact taken from the citizen. `source_span` is the evidence: the citizen's
    exact words. A field with no evidence is never filled in."""

    value: str = Field(min_length=1, max_length=MAX_FACT_CHARS)
    source_span: str = Field(min_length=1, max_length=MAX_TEXT_CHARS)
    source: FactSource = FactSource.CITIZEN_STATEMENT
    statement_index: int = Field(default=0, ge=0)  # which citizen statement it came from
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    method: FactMethod = "rule"  # rule | lexicon | ai | citizen
    quality: FactQuality = "clear"  # vague: e.g. "our street"; partial: subject without a problem


class ExtractedEntity(BaseModel):
    type: str = Field(pattern=r"^[a-z_]{2,32}$")  # landmark, place, identifier, organisation, other
    value: str = Field(min_length=1, max_length=MAX_FACT_CHARS)
    source_span: str = Field(min_length=1, max_length=MAX_TEXT_CHARS)
    source: FactSource = FactSource.CITIZEN_STATEMENT
    statement_index: int = Field(default=0, ge=0)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    method: FactMethod = "rule"
    quality: FactQuality = "clear"


class ExtractedGrievance(BaseModel):
    issue: ExtractedField | None = None
    location: ExtractedField | None = None
    duration: ExtractedField | None = None
    entities: list[ExtractedEntity] = Field(default_factory=list)

    def get(self, field: IntakeField) -> ExtractedField | None:
        return getattr(self, field.value)


class RejectedFact(BaseModel):
    """A fact a provider proposed that failed verification (e.g. its evidence is
    not in the citizen's words). Kept for audit; never used."""

    field: str
    value: str
    claimed_evidence: str | None
    reason: str


class FactEvidence(BaseModel):
    field: str
    value: str
    evidence: str
    source: FactSource
    method: FactMethod = "rule"


class ProviderTraceStep(BaseModel):
    """One step of the processing chain, for transparency. Never contains secrets."""

    stage: Literal[
        "input", "speech_to_text", "language", "extraction", "translation", "validation", "correction",
        # Phase 3 - classification
        "retrieval", "rules", "ai_reasoning", "department_mapping", "jurisdiction",
        # Phase 4 - drafting
        "drafting",
    ]
    provider: str
    outcome: Literal["used", "skipped", "unavailable", "failed", "rejected"]
    detail: str | None = None


# --------------------------------------------------------------------------
# Pipeline stages
# --------------------------------------------------------------------------


class LanguageDetectionResult(BaseModel):
    language: str  # ISO code, or "und" when undetermined
    confidence: float | None = None  # None unless the method really produces one
    method: DetectionMethod
    transliterated: bool = False  # e.g. Tamil written in Latin letters
    script: str | None = None
    supported: bool = True


class TranscriptInfo(BaseModel):
    text: str
    provider: str
    language: str | None = None
    confidence: float | None = None


class TranslationOutcome(BaseModel):
    status: TranslationStatus
    source_language: str
    target_language: str
    translated_text: str | None = None
    provider: str | None = None
    error: str | None = None


class ExtractionInfo(BaseModel):
    status: ExtractionStatus
    method: ExtractionMethod
    provider: str | None = None
    fallback_reason: str | None = None
    error: str | None = None


class MissingField(BaseModel):
    field: IntakeField
    requirement: FieldRequirement
    reason: str


class ClarificationQuestion(BaseModel):
    """A question for the citizen. Phase 2 asks about intake fields; Phase 3 reuses the
    same shape for "locality" (jurisdiction) and "category" (ambiguity)."""

    field: IntakeField | Literal["locality", "category"]
    text: str
    language: str


class CitizenStatement(BaseModel):
    kind: StatementKind
    text: str
    recorded_at: datetime


class CitizenCorrection(BaseModel):
    """A value the citizen supplied directly. `value=None` means the citizen said
    the extracted value is wrong and gave no replacement."""

    field: IntakeField
    value: str | None
    recorded_at: datetime
    evidence: str | None = None  # the citizen's own words when given as free text


class AudioPayload(BaseModel):
    content: bytes = Field(repr=False)
    content_type: str
    format: str  # detected from the file's bytes, not trusted from the client


# --------------------------------------------------------------------------
# Agent contract
# --------------------------------------------------------------------------


class IntakeRequest(BaseModel):
    complaint_id: str
    channel: InputChannel = InputChannel.TEXT
    text: str | None = Field(default=None, max_length=MAX_TEXT_CHARS)
    audio: AudioPayload | None = None
    language_hint: str | None = Field(default=None, pattern=LANGUAGE_CODE_PATTERN)
    clarifications: list[CitizenStatement] = Field(default_factory=list)
    corrections: list[CitizenCorrection] = Field(default_factory=list)

    @model_validator(mode="after")
    def _one_input(self) -> "IntakeRequest":
        if (self.text is None) == (self.audio is None):
            raise ValueError("Provide exactly one of text or audio")
        return self


class IntakeResponse(BaseModel):
    """IntakeResult: structured output of the UNDERSTAND stage and the handoff to
    Phase 3. Keeps its Phase 1 class name; `IntakeResult` is an alias."""

    complaint_id: str
    input_channel: InputChannel
    status: Literal[
        ComplaintStatus.CREATED, ComplaintStatus.NEEDS_INFO, ComplaintStatus.UNDERSTANDING, ComplaintStatus.UNDERSTOOD
    ]
    intake_status: IntakeStatus
    original_text: str  # the citizen's words, never overwritten
    transcript: TranscriptInfo | None = None
    language: LanguageDetectionResult
    processing_language: str
    translation: TranslationOutcome
    extracted: ExtractedGrievance
    rejected_facts: list[RejectedFact] = Field(default_factory=list)
    missing_information: list[MissingField] = Field(default_factory=list)
    clarification_questions: list[ClarificationQuestion] = Field(default_factory=list)
    extraction: ExtractionInfo
    confidence: float | None = None  # overall; None unless a provider reports one
    processing_mode: ProcessingMode = ProcessingMode.OFFLINE_RULE
    provider_trace: list[ProviderTraceStep] = Field(default_factory=list)
    safety_flags: list[str] = Field(default_factory=list)  # e.g. instruction_like_text (recorded, never obeyed)
    # Phase 3 adds category-specific required fields here without changing this contract.
    category_required_fields: list[str] = Field(default_factory=list)
    provider_metadata: dict[str, str | int | float | bool | None] = Field(default_factory=dict)
    citizen_confirmation_status: ConfirmationStatus
    clarifications: list[CitizenStatement] = Field(default_factory=list)
    corrections: list[CitizenCorrection] = Field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def language_source(self) -> str:
        return self.language.method.value

    @computed_field  # type: ignore[prop-decorator]
    @property
    def original_language(self) -> str:
        return self.language.language

    @computed_field  # type: ignore[prop-decorator]
    @property
    def detected_language(self) -> str:  # Phase 1 name
        return self.language.language

    @computed_field  # type: ignore[prop-decorator]
    @property
    def translated_text(self) -> str | None:
        return self.translation.translated_text

    @computed_field  # type: ignore[prop-decorator]
    @property
    def missing_fields(self) -> list[str]:  # Phase 1 name
        return [m.field.value for m in self.missing_information]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def follow_up_question(self) -> str | None:  # Phase 1 name
        return " ".join(q.text for q in self.clarification_questions) or None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def evidence(self) -> list[FactEvidence]:
        items: list[FactEvidence] = []
        for field in IntakeField:
            fact = self.extracted.get(field)
            if fact is not None:
                items.append(
                    FactEvidence(
                        field=field.value, value=fact.value, evidence=fact.source_span, source=fact.source, method=fact.method
                    )
                )
        for entity in self.extracted.entities:
            items.append(
                FactEvidence(
                    field=f"entity:{entity.type}", value=entity.value, evidence=entity.source_span,
                    source=entity.source, method=entity.method,
                )
            )
        return items


# Name used in the Phase 2 specification.
IntakeResult = IntakeResponse


# --------------------------------------------------------------------------
# HTTP request/response models
# --------------------------------------------------------------------------


class TextIntakeRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    raw_text: str = Field(min_length=1, max_length=MAX_TEXT_CHARS, description="Citizen's own words")
    language: str | None = Field(default=None, pattern=LANGUAGE_CODE_PATTERN)
    input_channel: InputChannel = Field(
        default=InputChannel.TEXT,
        description="'voice' when the text came from the browser's speech recognition",
    )

    @field_validator("raw_text")
    @classmethod
    def _sanitise(cls, value: str) -> str:
        cleaned = sanitize_text(value)
        if len(cleaned) < 3:
            raise ValueError("Complaint text is too short or empty after removing markup")
        return cleaned


class IntakeRerunRequest(BaseModel):
    language: str | None = Field(default=None, pattern=LANGUAGE_CODE_PATTERN)


class ClarificationAnswerRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    text: str = Field(min_length=1, max_length=MAX_ANSWER_CHARS)

    @field_validator("text")
    @classmethod
    def _sanitise(cls, value: str) -> str:
        cleaned = sanitize_text(value)
        if not cleaned:
            raise ValueError("Answer is empty after removing markup")
        return cleaned


class FieldCorrection(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    field: IntakeField
    value: str | None = Field(default=None, max_length=MAX_FACT_CHARS)

    @field_validator("value")
    @classmethod
    def _sanitise(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = sanitize_text(value)
        return cleaned or None


class IntakeCorrectionRequest(BaseModel):
    """Either structured corrections (edit form) or the citizen's own words
    ("No, it is 5 days"), parsed offline. Exactly one must be given."""

    corrections: list[FieldCorrection] | None = Field(default=None, min_length=1, max_length=len(IntakeField))
    text: str | None = Field(default=None, min_length=1, max_length=MAX_ANSWER_CHARS)

    @field_validator("text")
    @classmethod
    def _sanitise_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = sanitize_text(value)
        if not cleaned:
            raise ValueError("Correction is empty after removing markup")
        return cleaned

    @model_validator(mode="after")
    def _one_form(self) -> "IntakeCorrectionRequest":
        if (self.corrections is None) == (self.text is None):
            raise ValueError("Provide either 'corrections' or 'text'")
        if self.corrections is not None:
            fields = [c.field for c in self.corrections]
            if len(fields) != len(set(fields)):
                raise ValueError("Each field may be corrected once per request")
        return self


class IntakeHandoff(BaseModel):
    """What Phase 3 (classification) receives, only after the citizen confirms."""

    complaint_id: str
    original_text: str
    language: str
    issue: ExtractedField
    location: ExtractedField
    duration: ExtractedField | None
    entities: list[ExtractedEntity]
    evidence: list[FactEvidence]
    translated_text: str | None
    confirmation_status: ConfirmationStatus
    processing_mode: ProcessingMode


class LanguageInfo(BaseModel):
    code: str
    display_name: str
    native_name: str
    speech_locale: str
    text_intake: str
    speech_to_text: str
    translation: str
    ui: str
    notes: str
    offline_text: bool  # an offline resource file exists for this language
    local_extraction: Literal["tested", "configured", "unavailable"]
    voice: str  # "browser-dependent", plus server speech-to-text when configured


class IntakeCapabilities(BaseModel):
    processing_language: str
    languages: list[LanguageInfo]
    offline_first: bool
    ai_extraction_available: bool  # optional enhancement only
    rule_based_fallback_available: bool
    server_speech_to_text_available: bool
    speech_to_text_providers: list[str]
    max_audio_bytes: int
    accepted_audio_types: list[str]
