"""Citizen intake orchestration: API -> IntakeService -> IntakeAgent -> providers.

The service owns persistence, complaint state transitions and audit events. The
agent owns the understanding. Routes contain no business logic.

State: CREATED -> NEEDS_INFO <-> UNDERSTANDING --(citizen confirms)--> UNDERSTOOD.
Intake never moves a complaint to CLASSIFIED or beyond.
"""

from __future__ import annotations

from uuid import uuid4

from sqlalchemy.orm import Session

from app.agents.base import AgentContext
from app.agents.intake import IntakeAgent
from app.core.clock import Clock, get_clock
from app.core.config import Settings
from app.core.errors import AppError, ConflictError, NotFoundError
from app.core.languages import LanguageRegistry
from app.core.state_machine import ensure_transition
from app.models import ClassificationRecord, Complaint, IntakeRecord
from app.repositories import IntakeRepository
from app.schemas.audit import AuditEventCreate
from app.schemas.complaint import ComplaintCreateRequest
from app.schemas.enums import ActorType, AuditEventType, ComplaintStatus, InputChannel
from app.schemas.intake import (
    AudioPayload,
    CitizenCorrection,
    CitizenStatement,
    ConfirmationStatus,
    ExtractionStatus,
    FieldRequirement,
    IntakeCapabilities,
    IntakeCorrectionRequest,
    IntakeHandoff,
    IntakeRequest,
    IntakeResult,
    IntakeStatus,
    LanguageInfo,
    StatementKind,
    TextIntakeRequest,
    TranslationStatus,
)
from app.services.audit_service import AuditService
from app.services.complaint_service import ComplaintService
from app.services.intake.speech_to_text import ACCEPTED_CONTENT_TYPES, validate_audio

# Once a complaint has moved past intake (Phase 3+), intake can no longer change it.
_INTAKE_STATUSES = {
    ComplaintStatus.CREATED,
    ComplaintStatus.NEEDS_INFO,
    ComplaintStatus.UNDERSTANDING,
    ComplaintStatus.UNDERSTOOD,
}
_AGENT = "intake"


# Statuses in which a citizen-confirmed intake may be handed to (or be in) Phase 3.
_CONFIRMED_STATUSES = {
    ComplaintStatus.UNDERSTOOD,
    ComplaintStatus.CLASSIFYING,
    ComplaintStatus.CLASSIFIED,
    ComplaintStatus.NEEDS_INFO,
    ComplaintStatus.NEEDS_REVIEW,
}


class CorrectionNotUnderstoodError(AppError):
    status_code = 422
    code = "correction_not_understood"


class NotConfirmedError(ConflictError):
    code = "intake_not_confirmed"


def build_handoff(complaint: Complaint, result: IntakeResult) -> IntakeHandoff:
    """The Phase 2 -> Phase 3 contract. Refuses anything the citizen has not confirmed.

    A correction after confirmation resets the confirmation, so a CONFIRMED result
    always holds the latest facts the citizen confirmed.
    """
    if (
        result.citizen_confirmation_status is not ConfirmationStatus.CONFIRMED
        or complaint.status not in _CONFIRMED_STATUSES
        or result.extracted.issue is None
        or result.extracted.location is None
    ):
        raise NotConfirmedError("The citizen has not confirmed the intake yet")
    return IntakeHandoff(
        complaint_id=complaint.id,
        original_text=result.original_text,
        language=result.language.language,
        issue=result.extracted.issue,
        location=result.extracted.location,
        duration=result.extracted.duration,
        entities=result.extracted.entities,
        evidence=result.evidence,
        translated_text=result.translated_text,
        confirmation_status=result.citizen_confirmation_status,
        processing_mode=result.processing_mode,
    )


class IntakeService:
    def __init__(
        self,
        session: Session,
        agent: IntakeAgent,
        registry: LanguageRegistry,
        settings: Settings,
        clock: Clock | None = None,
    ) -> None:
        self.clock = clock or get_clock()
        self.session = session
        self.agent = agent
        self.registry = registry
        self.settings = settings
        self.complaints = ComplaintService(session, self.clock)
        self.audit = AuditService(session, self.clock)
        self.records = IntakeRepository(session)

    # ------------------------------------------------------------------ queries

    def capabilities(self) -> IntakeCapabilities:
        stt = self.agent.transcription
        stt_names = list(getattr(stt, "available_names", [])) or ([stt.name] if stt.available else [])
        voice = "browser-dependent" + (f"; server: {', '.join(stt_names)}" if stt_names else "")
        return IntakeCapabilities(
            processing_language=self.registry.processing_language,
            languages=[
                LanguageInfo(
                    code=lang.code,
                    display_name=lang.display_name,
                    native_name=lang.native_name,
                    speech_locale=lang.speech_locale,
                    text_intake=lang.support.text_intake.value,
                    speech_to_text=lang.support.speech_to_text.value,
                    translation=lang.support.translation.value,
                    ui=lang.support.ui.value,
                    notes=lang.notes,
                    offline_text=self.agent.offline.supports(lang.code),
                    local_extraction=(
                        "unavailable" if not self.agent.offline.supports(lang.code)
                        else "tested" if lang.support.text_intake.value == "SUPPORTED"
                        else "configured"
                    ),
                    voice=voice,
                )
                for lang in self.registry.enabled()
            ],
            offline_first=True,
            ai_extraction_available=self.agent.ai_extractor.available,
            rule_based_fallback_available=True,
            server_speech_to_text_available=stt.available,
            speech_to_text_providers=["browser_speech", *stt_names],
            max_audio_bytes=self.settings.max_audio_bytes,
            accepted_audio_types=sorted(ACCEPTED_CONTENT_TYPES),
        )

    def get_result(self, complaint_id: str) -> IntakeResult:
        self.complaints.get(complaint_id)
        record = self.records.get(complaint_id)
        if record is None:
            raise NotFoundError(f"Complaint {complaint_id!r} has not been through intake yet")
        return IntakeResult.model_validate(record.result)

    def handoff(self, complaint_id: str) -> IntakeHandoff:
        """The contract Phase 3 consumes. Only confirmed intakes."""
        complaint = self.complaints.get(complaint_id)
        return build_handoff(complaint, self.get_result(complaint_id))

    # ------------------------------------------------------------------ commands

    async def submit_text(self, request: TextIntakeRequest) -> IntakeResult:
        if request.language:
            self.registry.require_enabled(request.language)
        complaint = self.complaints.create(
            ComplaintCreateRequest(
                citizen_input=request.raw_text, language=request.language, channel=request.input_channel
            )
        )
        self._record_received(complaint, request.input_channel, request.language)
        return await self._run(complaint, text=request.raw_text, language=request.language)

    async def submit_voice(self, audio: bytes, content_type: str | None, language: str | None) -> IntakeResult:
        if language:
            self.registry.require_enabled(language)
        audio_format = validate_audio(
            audio, content_type, max_bytes=self.settings.max_audio_bytes, max_seconds=self.settings.max_audio_seconds
        )
        complaint_id = str(uuid4())
        payload = AudioPayload(content=audio, content_type=content_type or "", format=audio_format)
        # Transcribe first: without a transcript there is no citizen text to store.
        result = await self.agent.execute(
            IntakeRequest(complaint_id=complaint_id, channel=InputChannel.VOICE, audio=payload, language_hint=language),
            AgentContext(complaint_id=complaint_id, clock=self.clock),
        )
        complaint = self.complaints.create(
            ComplaintCreateRequest(citizen_input=result.original_text, language=language, channel=InputChannel.VOICE),
            complaint_id=complaint_id,
        )
        self._record_received(complaint, InputChannel.VOICE, language)
        self._record_transcription(complaint, result)
        return self._persist(complaint, result, previous=None)

    async def process(self, complaint_id: str, language: str | None) -> IntakeResult:
        """Run (or retry) intake for a complaint still in CREATED."""
        complaint = self._intake_complaint(complaint_id)
        if complaint.status is not ComplaintStatus.CREATED:
            raise ConflictError("Intake has already succeeded; answer questions or correct facts instead")
        if language:
            self.registry.require_enabled(language)
        record = self.records.get(complaint_id)
        if record is None:
            self._record_received(complaint, complaint.input_channel, language)
        return await self._run(complaint, text=complaint.citizen_input, language=language or complaint.language, record=record)

    async def answer(self, complaint_id: str, text: str) -> IntakeResult:
        complaint = self._intake_complaint(complaint_id)
        record = self._record(complaint_id)
        if record.intake_status in (IntakeStatus.FAILED, IntakeStatus.NEEDS_LANGUAGE):
            raise ConflictError("Intake did not complete; retry it before answering questions")
        statement = CitizenStatement(kind=StatementKind.CLARIFICATION, text=text, recorded_at=self.clock.now())
        record.clarifications = [*record.clarifications, statement.model_dump(mode="json")]
        self.audit.record(
            AuditEventCreate(
                complaint_id=complaint_id,
                event_type=AuditEventType.INTAKE_CLARIFICATION_ANSWERED,
                actor_type=ActorType.CITIZEN,
                actor_name="citizen",
                summary="Citizen answered a clarification question",
                payload={"clarification_number": len(record.clarifications), "characters": len(text)},
            )
        )
        language = IntakeResult.model_validate(record.result).language.language
        return await self._run(complaint, text=complaint.citizen_input, language=language, record=record)

    def correct(self, complaint_id: str, request: IntakeCorrectionRequest) -> IntakeResult:
        complaint = self._intake_complaint(complaint_id)
        record = self._record(complaint_id)
        previous = IntakeResult.model_validate(record.result)
        now = self.clock.now()
        if request.text is not None:
            parsed = self.agent.parse_correction(request.text, previous.language.language)
            if not parsed:
                raise CorrectionNotUnderstoodError(
                    "I could not tell which detail to change. Please use Edit to correct a field directly"
                )
            new = [CitizenCorrection(field=f, value=v, evidence=e, recorded_at=now) for f, v, e in parsed]
        else:
            new = [CitizenCorrection(field=c.field, value=c.value, recorded_at=now) for c in request.corrections or []]
        all_corrections = [CitizenCorrection.model_validate(c) for c in record.corrections] + new
        record.corrections = [c.model_dump(mode="json") for c in all_corrections]
        self.audit.record(
            AuditEventCreate(
                complaint_id=complaint_id,
                event_type=AuditEventType.INTAKE_CORRECTED,
                actor_type=ActorType.CITIZEN,
                actor_name="citizen",
                summary="Citizen corrected: " + ", ".join(c.field.value for c in new),
                payload={"fields": [c.field.value for c in new], "form": "text" if request.text else "fields"},
                evidence=[
                    {"field": c.field.value, "citizen_value": c.value, "citizen_words": c.evidence, "source": "citizen_correction"}
                    for c in new
                ],
            )
        )
        result = self.agent.reevaluate(previous, all_corrections)
        return self._persist(complaint, result, previous=previous, record=record, audit_run=False)

    def confirm(self, complaint_id: str) -> IntakeResult:
        complaint = self._intake_complaint(complaint_id)
        record = self._record(complaint_id)
        result = IntakeResult.model_validate(record.result)
        if result.citizen_confirmation_status is ConfirmationStatus.CONFIRMED:
            return result
        if result.intake_status is not IntakeStatus.COMPLETED:
            missing = ", ".join(
                m.field.value for m in result.missing_information if m.requirement is FieldRequirement.REQUIRED_TO_CONTINUE
            )
            raise ConflictError(f"Cannot confirm yet: required information is missing ({missing or 'intake incomplete'})")
        now = self.clock.now()
        ensure_transition(complaint.status, ComplaintStatus.UNDERSTOOD)
        complaint.status = ComplaintStatus.UNDERSTOOD
        complaint.updated_at = now
        result = result.model_copy(update={
            "status": ComplaintStatus.UNDERSTOOD,
            "citizen_confirmation_status": ConfirmationStatus.CONFIRMED,
            "updated_at": now,
        })
        record.result = result.model_dump(mode="json")
        record.confirmation_status = ConfirmationStatus.CONFIRMED
        record.updated_at = now
        self.audit.record(
            AuditEventCreate(
                complaint_id=complaint_id,
                event_type=AuditEventType.INTAKE_CONFIRMED,
                actor_type=ActorType.CITIZEN,
                actor_name="citizen",
                summary="Citizen confirmed what SPANDAN AI understood",
                evidence=[e.model_dump(mode="json") for e in result.evidence],
            )
        )
        self.audit.record(
            AuditEventCreate(
                complaint_id=complaint_id,
                event_type=AuditEventType.COMPLAINT_UNDERSTOOD,
                actor_type=ActorType.AGENT,
                actor_name=_AGENT,
                summary="Complaint UNDERSTOOD (confirmed by the citizen); ready for Phase 3",
                payload={"processing_mode": result.processing_mode.value},
            )
        )
        return result

    # ------------------------------------------------------------------ internals

    def _intake_complaint(self, complaint_id: str) -> Complaint:
        complaint = self.complaints.get(complaint_id)
        if complaint.status not in _INTAKE_STATUSES:
            raise ConflictError(f"Complaint is {complaint.status.value}; intake can no longer change it")
        if self.session.get(ClassificationRecord, complaint_id) is not None:
            # NEEDS_INFO here belongs to Phase 3; its questions are answered there.
            raise ConflictError(
                "Complaint is in classification; answer its questions via /classification/{id}/answer"
            )
        return complaint

    def _record(self, complaint_id: str) -> IntakeRecord:
        record = self.records.get(complaint_id)
        if record is None:
            raise NotFoundError(f"Complaint {complaint_id!r} has not been through intake yet")
        return record

    async def _run(
        self, complaint: Complaint, *, text: str, language: str | None, record: IntakeRecord | None = None
    ) -> IntakeResult:
        previous = IntakeResult.model_validate(record.result) if record else None
        clarifications = [CitizenStatement.model_validate(c) for c in (record.clarifications if record else [])]
        corrections = [CitizenCorrection.model_validate(c) for c in (record.corrections if record else [])]
        result = await self.agent.execute(
            IntakeRequest(
                complaint_id=complaint.id,
                channel=complaint.input_channel,
                text=text,
                language_hint=language if language and self.registry.is_enabled(language) else None,
                clarifications=clarifications,
                corrections=corrections,
            ),
            AgentContext(complaint_id=complaint.id, clock=self.clock),
        )
        if previous is not None and previous.transcript is not None:
            result = result.model_copy(update={"transcript": previous.transcript, "input_channel": previous.input_channel})
        return self._persist(complaint, result, previous=previous, record=record)

    def _record_received(self, complaint: Complaint, channel: InputChannel, language: str | None) -> None:
        self.audit.record(
            AuditEventCreate(
                complaint_id=complaint.id,
                event_type=AuditEventType.INTAKE_RECEIVED,
                actor_type=ActorType.CITIZEN,
                actor_name="citizen",
                summary=f"Grievance received by {channel.value}",
                payload={"channel": channel.value, "language_chosen": language, "characters": len(complaint.citizen_input)},
            )
        )

    def _record_transcription(self, complaint: Complaint, result: IntakeResult) -> None:
        if result.transcript is None:
            return
        self.audit.record(
            AuditEventCreate(
                complaint_id=complaint.id,
                event_type=AuditEventType.COMPLAINT_TRANSCRIBED,
                actor_type=ActorType.AGENT,
                actor_name=_AGENT,
                summary=f"Voice recording transcribed ({result.transcript.provider})",
                payload={
                    "provider": result.transcript.provider,
                    "characters": len(result.transcript.text),
                    "confidence": result.transcript.confidence,
                },
            )
        )

    def _persist(
        self,
        complaint: Complaint,
        result: IntakeResult,
        *,
        previous: IntakeResult | None,
        record: IntakeRecord | None = None,
        audit_run: bool = True,
    ) -> IntakeResult:
        now = self.clock.now()
        if record is None:
            record = self.records.get(complaint.id) or IntakeRecord(
                complaint_id=complaint.id, clarifications=[], corrections=[], created_at=now
            )
        result = result.model_copy(update={"created_at": record.created_at, "updated_at": now})
        record.result = result.model_dump(mode="json")
        record.intake_status = result.intake_status
        record.confirmation_status = result.citizen_confirmation_status
        record.original_language = result.language.language if result.language.supported else None
        record.translated_text = result.translated_text
        record.updated_at = now
        self.records.save(record)

        # Complaint row: extracted facts are copied; the citizen's original text is never touched.
        if result.language.supported:
            complaint.language = result.language.language
        complaint.issue = result.extracted.issue.value if result.extracted.issue else None
        complaint.location = result.extracted.location.value if result.extracted.location else None
        complaint.duration = result.extracted.duration.value if result.extracted.duration else None
        if result.status is not complaint.status:
            ensure_transition(complaint.status, result.status)
            complaint.status = result.status
        complaint.updated_at = now

        if audit_run:
            self._audit_run(complaint.id, result, previous)
        self._audit_outcome(complaint.id, result, previous)
        return result

    def _event(self, complaint_id: str, event_type: AuditEventType, summary: str, **fields: object) -> None:
        self.audit.record(
            AuditEventCreate(
                complaint_id=complaint_id,
                event_type=event_type,
                actor_type=ActorType.AGENT,
                actor_name=_AGENT,
                summary=summary,
                **fields,  # type: ignore[arg-type]
            )
        )

    def _audit_run(self, complaint_id: str, result: IntakeResult, previous: IntakeResult | None) -> None:
        language = result.language
        if previous is None or previous.language.language != language.language:
            self.audit.record(
                AuditEventCreate(
                    complaint_id=complaint_id,
                    event_type=AuditEventType.INTAKE_LANGUAGE_DETECTED,
                    actor_type=ActorType.CITIZEN if language.method.value == "declared" else ActorType.AGENT,
                    actor_name="citizen" if language.method.value == "declared" else _AGENT,
                    summary=f"Language {language.language} ({language.method.value})",
                    payload=language.model_dump(mode="json"),
                )
            )
        translation = result.translation
        if translation.status is TranslationStatus.TRANSLATED:
            self._event(
                complaint_id, AuditEventType.COMPLAINT_TRANSLATED,
                f"Translated {translation.source_language} to {translation.target_language} (original kept)",
                payload={"provider": translation.provider},
            )
        elif translation.status is TranslationStatus.FAILED:
            self._event(
                complaint_id, AuditEventType.INTAKE_TRANSLATION_FAILED,
                "Translation failed; original text preserved, no translation stored",
                payload={"provider": translation.provider, "error": translation.error},
            )

        trace = [step.model_dump(mode="json") for step in result.provider_trace]
        if result.extraction.status is ExtractionStatus.COMPLETED:
            self._event(
                complaint_id, AuditEventType.INTAKE_FACTS_EXTRACTED,
                f"Extracted {len(result.evidence)} fact(s) with evidence ({result.processing_mode.value})",
                payload={
                    "processing_mode": result.processing_mode.value,
                    "method": result.extraction.method.value,
                    "provider_trace": trace,
                    "safety_flags": result.safety_flags,
                },
                evidence=[e.model_dump(mode="json") for e in result.evidence],
            )
        else:
            self._event(
                complaint_id, AuditEventType.INTAKE_FAILED,
                f"Intake could not complete ({result.intake_status.value}); nothing was guessed",
                payload={"intake_status": result.intake_status.value, "error": result.extraction.error, "provider_trace": trace},
            )
        if result.rejected_facts:
            self._event(
                complaint_id, AuditEventType.INTAKE_FACTS_REJECTED,
                f"Rejected {len(result.rejected_facts)} unsupported fact(s)",
                payload={"rejected": [r.model_dump(mode="json") for r in result.rejected_facts]},
            )

    def _audit_outcome(self, complaint_id: str, result: IntakeResult, previous: IntakeResult | None) -> None:
        if previous is not None and previous.status is result.status and previous.missing_fields == result.missing_fields:
            return  # no change worth recording
        required = [m for m in result.missing_information if m.requirement is FieldRequirement.REQUIRED_TO_CONTINUE]
        if required:
            self._event(
                complaint_id, AuditEventType.INTAKE_MISSING_INFO_DETECTED,
                "Missing: " + ", ".join(m.field.value for m in required),
                payload={"missing": [m.model_dump(mode="json") for m in result.missing_information]},
            )
        if result.clarification_questions:
            self._event(
                complaint_id, AuditEventType.COMPLAINT_INFO_REQUESTED,
                "Asked the citizen for: " + ", ".join(q.field.value for q in result.clarification_questions),
                payload={"questions": [q.model_dump(mode="json") for q in result.clarification_questions]},
            )
