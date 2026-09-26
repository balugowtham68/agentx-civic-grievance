"""Agent 1 - Citizen Intake (Phase 2): the UNDERSTAND stage, OFFLINE FIRST.

Pipeline:
    input gateway (text, browser-transcribed voice, or uploaded audio -> local STT first)
    -> language: citizen's choice, else script -> romanised-word heuristics -> optional AI
    -> OfflineIntakeEngine (rules + language lexicons; no network, no key)
    -> optional AI provider, ONLY for required facts the offline engine did not find
    -> evidence validator (same for every layer)
    -> citizen corrections (newest citizen input wins)
    -> missing information + clarification questions
    -> IntakeResult with processing_mode and provider_trace

The agent never classifies (Phase 3), never writes the database and never calls
a model SDK directly: providers are injected. External AI is never required.
"""

from __future__ import annotations

import asyncio
from datetime import datetime

from app.agents.base import AgentContext, BaseAgent
from app.agents.intake.policy import clarification_questions, has_blocking_gap, missing_information
from app.agents.intake.verification import verify_facts
from app.core.languages import LanguageRegistry
from app.core.logging import get_logger
from app.core.security import sanitize_text
from app.prompts.intake import EXTRACTION_PROMPT_VERSION
from app.schemas.enums import AgentName, ComplaintStatus, InputChannel
from app.schemas.intake import (
    CitizenCorrection,
    CitizenStatement,
    ConfirmationStatus,
    DetectionMethod,
    ExtractedField,
    ExtractedGrievance,
    ExtractionInfo,
    ExtractionMethod,
    ExtractionStatus,
    FactSource,
    IntakeField,
    IntakeRequest,
    IntakeResult,
    IntakeStatus,
    LanguageDetectionResult,
    ProcessingMode,
    ProviderTraceStep,
    RejectedFact,
    TranscriptInfo,
    TranslationOutcome,
    TranslationStatus,
)
from app.services.ai import AIProvider, AIProviderError
from app.services.external import LanguageDetector, TranscriptionProvider, TranslationProvider
from app.services.intake.extraction import AIFactExtractor, FactExtractor, ProposedFacts
from app.services.intake.language_detection import (
    UNDETERMINED,
    AILanguageDetector,
    CompositeLanguageDetector,
    LatinHeuristicDetector,
    ScriptLanguageDetector,
)
from app.services.intake.offline.engine import OfflineIntakeEngine
from app.services.intake.offline.resources import load_resources, load_safety
from app.services.intake.offline.text import normalise
from app.services.intake.speech_to_text import ChainTranscriptionProvider, InvalidAudioError
from app.services.intake.translation import AITranslationProvider

logger = get_logger(__name__)
LOCAL_MODEL_PROVIDERS = {"local_whisper"}


class IntakeAgent(BaseAgent[IntakeRequest, IntakeResult]):
    name = AgentName.INTAKE
    description = "Understands the citizen's grievance from voice or text in their language, offline first"
    phase = 2
    input_model = IntakeRequest
    output_model = IntakeResult

    def __init__(
        self,
        ai: AIProvider,
        transcription: TranscriptionProvider | None = None,
        translation: TranslationProvider | None = None,
        *,
        language_detector: LanguageDetector | None = None,
        offline_engine: OfflineIntakeEngine | None = None,
        ai_extractor: FactExtractor | None = None,
        registry: LanguageRegistry | None = None,
    ) -> None:
        self.ai = ai
        self.registry = registry or LanguageRegistry.load()
        self.offline = offline_engine or OfflineIntakeEngine(load_resources(), load_safety())
        self.transcription = transcription or ChainTranscriptionProvider([])
        self.translation = translation or AITranslationProvider(ai)
        self.language_detector = language_detector or CompositeLanguageDetector(
            ScriptLanguageDetector(self.registry),
            AILanguageDetector(ai, self.registry),
            LatinHeuristicDetector(
                {
                    code: {normalise(w) for w in self.offline.resources(code).latin_markers}  # type: ignore[union-attr]
                    for code in self.offline.languages
                    if self.registry.is_enabled(code)
                }
            ),
        )
        self.ai_extractor = ai_extractor or AIFactExtractor(ai)

    # ------------------------------------------------------------------ stages

    async def _transcribe(
        self, payload: IntakeRequest, trace: list[ProviderTraceStep]
    ) -> tuple[str, TranscriptInfo | None]:
        if payload.audio is None:
            if payload.channel is InputChannel.VOICE:
                trace.append(ProviderTraceStep(
                    stage="speech_to_text", provider="browser_speech", outcome="used",
                    detail="Transcribed on the citizen's device; no audio sent",
                ))
            return payload.text or "", None
        transcript = await self.transcription.transcribe(
            payload.audio.content, audio_format=payload.audio.format, language_hint=payload.language_hint
        )
        text = sanitize_text(transcript.text)[:2000]
        if len(text) < 3:
            raise InvalidAudioError("No usable speech was recognised. Please try again or type your complaint")
        trace.append(ProviderTraceStep(stage="speech_to_text", provider=transcript.provider, outcome="used"))
        return text, TranscriptInfo(
            text=text, provider=transcript.provider, language=transcript.language, confidence=transcript.confidence
        )

    async def _language(self, text: str, hint: str | None, trace: list[ProviderTraceStep]) -> LanguageDetectionResult:
        if hint:
            code = hint.split("-")[0]
            trace.append(ProviderTraceStep(stage="language", provider="citizen_choice", outcome="used", detail=code))
            return LanguageDetectionResult(language=code, method=DetectionMethod.DECLARED, supported=self.registry.is_enabled(code))
        detected = await self.language_detector.detect(text)
        trace.append(ProviderTraceStep(
            stage="language",
            provider={"script": "unicode_script", "heuristic": "romanised_word_heuristics",
                      "provider": "optional_ai", "default": "default"}.get(detected.method, detected.method),
            outcome="used",
            detail=detected.language,
        ))
        return LanguageDetectionResult(
            language=detected.language,
            confidence=detected.confidence,
            method=DetectionMethod(detected.method),
            transliterated=detected.transliterated,
            script=detected.script,
            supported=detected.language != UNDETERMINED and self.registry.is_enabled(detected.language),
        )

    async def _translate(self, text: str, language: str, trace: list[ProviderTraceStep]) -> TranslationOutcome:
        target = self.registry.processing_language
        base = TranslationOutcome(status=TranslationStatus.NOT_REQUIRED, source_language=language, target_language=target)
        if language == target:
            return base
        if not self.translation.available:
            trace.append(ProviderTraceStep(
                stage="translation", provider="none", outcome="unavailable",
                detail="No offline translation model; the original text is used",
            ))
            return base.model_copy(update={
                "status": TranslationStatus.UNAVAILABLE,
                "error": "Translation is not available offline; the citizen's original words are used",
            })
        try:
            result = await self.translation.translate(text, source_language=language, target_language=target)
        except AIProviderError as exc:
            trace.append(ProviderTraceStep(stage="translation", provider=self.translation.name, outcome="failed", detail=exc.code))
            return base.model_copy(update={"status": TranslationStatus.FAILED, "provider": self.translation.name, "error": exc.message})
        trace.append(ProviderTraceStep(stage="translation", provider=result.provider, outcome="used"))
        return base.model_copy(update={"status": TranslationStatus.TRANSLATED, "translated_text": result.text, "provider": result.provider})

    def _offline(
        self, statements: list[str], language: str, trace: list[ProviderTraceStep]
    ) -> ProposedFacts | None:
        if not self.offline.supports(language):
            trace.append(ProviderTraceStep(stage="extraction", provider=self.offline.name, outcome="unavailable",
                                           detail=f"No offline resources for {language}"))
            return None
        try:
            proposed = self.offline.extract_sync(statements, language=language)
        except Exception as exc:  # noqa: BLE001 - a local failure must not lose the complaint
            logger.exception("offline intake engine failed", extra={"language": language})
            trace.append(ProviderTraceStep(stage="extraction", provider=self.offline.name, outcome="failed",
                                           detail=type(exc).__name__))
            return None
        trace.append(ProviderTraceStep(stage="extraction", provider=self.offline.name, outcome="used", detail=language))
        return proposed

    async def _ai_fill(
        self, statements: list[str], language: str, trace: list[ProviderTraceStep]
    ) -> ProposedFacts | None:
        try:
            proposed = await self.ai_extractor.extract(statements, language=language)
        except AIProviderError as exc:
            trace.append(ProviderTraceStep(stage="extraction", provider=self.ai_extractor.name, outcome="failed", detail=exc.code))
            return None
        trace.append(ProviderTraceStep(stage="extraction", provider=self.ai_extractor.name, outcome="used",
                                       detail="optional enhancement for missing facts"))
        return proposed

    # ------------------------------------------------------------------ corrections & finalisation

    @staticmethod
    def _apply_corrections(
        extracted: ExtractedGrievance,
        corrections: list[CitizenCorrection],
        clarifications: list[CitizenStatement],
    ) -> ExtractedGrievance:
        """Newest citizen input wins: an explicit correction overrides an extracted
        fact unless that fact came from a clarification given after the correction."""
        statement_times: list[datetime | None] = [None] + [c.recorded_at for c in clarifications]
        latest: dict[IntakeField, CitizenCorrection] = {}
        for correction in sorted(corrections, key=lambda c: c.recorded_at):
            latest[correction.field] = correction
        for field, correction in latest.items():
            fact = extracted.get(field)
            if fact is not None and fact.source is FactSource.CITIZEN_STATEMENT:
                index = fact.statement_index
                fact_time = statement_times[index] if index < len(statement_times) else None
                if fact_time is not None and fact_time > correction.recorded_at:
                    continue
            setattr(
                extracted,
                field.value,
                None
                if correction.value is None
                else ExtractedField(
                    value=correction.value,
                    source_span=correction.evidence or correction.value,
                    source=FactSource.CITIZEN_CORRECTION,
                    method="citizen",
                ),
            )
        return extracted

    @staticmethod
    def _processing_mode(result: IntakeResult) -> ProcessingMode:
        facts: list[object] = [f for f in (result.extracted.issue, result.extracted.location, result.extracted.duration) if f]
        facts += result.extracted.entities
        methods = {getattr(f, "method") for f in facts}
        ai_used = "ai" in methods or result.translation.status is TranslationStatus.TRANSLATED
        offline_used = bool(methods & {"rule", "lexicon"})
        if ai_used and offline_used:
            return ProcessingMode.MIXED
        if ai_used:
            return ProcessingMode.OPTIONAL_AI
        if result.transcript is not None and result.transcript.provider in LOCAL_MODEL_PROVIDERS:
            return ProcessingMode.OFFLINE_LOCAL_MODEL
        return ProcessingMode.OFFLINE_RULE

    def _finalise(self, result: IntakeResult) -> IntakeResult:
        """Derive missing information, questions, status and confirmation from the facts.
        Citizen corrections count as information even if automatic extraction failed.
        UNDERSTOOD is never set here: only citizen confirmation sets it (IntakeService)."""
        ran = result.extraction.status is ExtractionStatus.COMPLETED or bool(result.corrections)
        missing = missing_information(result.extracted, extraction_ran=ran)
        if not ran:
            status, intake_status = ComplaintStatus.CREATED, IntakeStatus.FAILED
        elif has_blocking_gap(missing):
            status, intake_status = ComplaintStatus.NEEDS_INFO, IntakeStatus.NEEDS_INFO
        else:
            status, intake_status = ComplaintStatus.UNDERSTANDING, IntakeStatus.COMPLETED
        language = result.language.language
        own = self.offline.resources(language)
        resources = own or self.offline.resources("en")
        issue = result.extracted.issue.value if result.extracted.issue else None
        questions = (
            clarification_questions(
                missing,
                templates=resources.questions,  # type: ignore[union-attr]
                language=language if own else "en",
                issue=issue,
            )
            if ran
            else []
        )
        finalised = result.model_copy(update={
            "missing_information": missing,
            "clarification_questions": questions,
            "status": status,
            "intake_status": intake_status,
            "citizen_confirmation_status": (
                ConfirmationStatus.PENDING if intake_status is IntakeStatus.COMPLETED else ConfirmationStatus.NOT_READY
            ),
        })
        return finalised.model_copy(update={"processing_mode": self._processing_mode(finalised)})

    def reevaluate(self, result: IntakeResult, corrections: list[CitizenCorrection]) -> IntakeResult:
        """Apply citizen corrections to an existing result. No provider is called."""
        if result.intake_status is IntakeStatus.NEEDS_LANGUAGE:
            return result.model_copy(update={"corrections": corrections})
        extracted = self._apply_corrections(result.extracted.model_copy(deep=True), corrections, result.clarifications)
        trace = [*result.provider_trace, ProviderTraceStep(stage="correction", provider="citizen", outcome="used")]
        return self._finalise(
            result.model_copy(update={"extracted": extracted, "corrections": corrections, "provider_trace": trace})
        )

    def parse_correction(self, text: str, language: str) -> list[tuple[IntakeField, str, str]]:
        """Offline parsing of a free-text correction ("No, it is 5 days").
        Returns (field, value, citizen's words) only for facts backed by the text."""
        proposed = self.offline.parse_correction(text, language=language)
        accepted, _ = verify_facts(proposed, [text])
        found: list[tuple[IntakeField, str, str]] = []
        for field in IntakeField:
            fact = accepted.get(field)
            if fact is not None and fact.quality != "partial":
                found.append((field, fact.value, fact.source_span))
        return found

    # ------------------------------------------------------------------ run

    async def _run(self, payload: IntakeRequest, context: AgentContext) -> IntakeResult:
        trace: list[ProviderTraceStep] = []
        original, transcript = await self._transcribe(payload, trace)
        statements = [original] + [c.text for c in payload.clarifications]
        safety_flags = sorted({flag for s in statements for flag in self.offline.safety_flags(s)})
        language = await self._language(original, payload.language_hint, trace)
        processing = self.registry.processing_language

        common = {
            "complaint_id": payload.complaint_id,
            "input_channel": payload.channel,
            "original_text": original,
            "transcript": transcript,
            "language": language,
            "processing_language": processing,
            "clarifications": payload.clarifications,
            "corrections": payload.corrections,
            "safety_flags": safety_flags,
        }

        if not language.supported:
            return IntakeResult(
                **common,
                status=ComplaintStatus.CREATED,
                intake_status=IntakeStatus.NEEDS_LANGUAGE,
                translation=TranslationOutcome(
                    status=TranslationStatus.UNAVAILABLE, source_language=language.language, target_language=processing,
                    error="Language not supported or not detected",
                ),
                extracted=ExtractedGrievance(),
                missing_information=missing_information(ExtractedGrievance(), extraction_ran=False),
                extraction=ExtractionInfo(
                    status=ExtractionStatus.NOT_RUN, method=ExtractionMethod.NONE,
                    error="Please choose your language from the supported list",
                ),
                citizen_confirmation_status=ConfirmationStatus.NOT_READY,
                provider_trace=trace,
                provider_metadata={"language_detection": language.method.value},
            )

        # 1. Offline engine (always first, no network).
        offline_proposed = self._offline(statements, language.language, trace)
        rejected: list[RejectedFact] = []
        extracted = ExtractedGrievance()
        if offline_proposed is not None:
            extracted, rejected = verify_facts(offline_proposed, statements)
        if rejected:
            trace.append(ProviderTraceStep(stage="validation", provider=self.offline.name, outcome="rejected",
                                           detail=f"{len(rejected)} fact(s) rejected"))

        # 2. Optional AI, only for required facts the offline engine could not find,
        #    in parallel with optional translation.
        needs_ai = extracted.issue is None or extracted.location is None
        use_ai = needs_ai and self.ai_extractor.available
        if needs_ai and not self.ai_extractor.available:
            trace.append(ProviderTraceStep(stage="extraction", provider="optional_ai", outcome="unavailable",
                                           detail="Not configured or offline; the citizen will be asked instead"))

        async def no_ai() -> None:
            return None

        ai_proposed, translation = await asyncio.gather(
            self._ai_fill(statements, language.language, trace) if use_ai else no_ai(),
            self._translate("\n".join(statements), language.language, trace),
        )

        ai_facts = 0
        if ai_proposed is not None:
            ai_accepted, ai_rejected = verify_facts(ai_proposed, statements)
            rejected += ai_rejected
            for field in IntakeField:
                if extracted.get(field) is None and ai_accepted.get(field) is not None:
                    setattr(extracted, field.value, ai_accepted.get(field))
                    ai_facts += 1
            known = {(e.type, normalise(e.value)) for e in extracted.entities}
            for entity in ai_accepted.entities:
                if (entity.type, normalise(entity.value)) not in known:
                    extracted.entities.append(entity)
            if ai_rejected:
                trace.append(ProviderTraceStep(stage="validation", provider=self.ai_extractor.name, outcome="rejected",
                                               detail=f"{len(ai_rejected)} unsupported fact(s) rejected"))

        extracted = self._apply_corrections(extracted, payload.corrections, payload.clarifications)

        offline_ok, ai_ok = offline_proposed is not None, ai_proposed is not None
        if offline_ok or ai_ok:
            method = (
                ExtractionMethod.MIXED if offline_ok and ai_facts
                else ExtractionMethod.AI_PROVIDER if not offline_ok
                else ExtractionMethod.OFFLINE_RULES
            )
            providers = [name for name, ok in ((self.offline.name, offline_ok), (self.ai_extractor.name, ai_ok)) if ok]
            extraction = ExtractionInfo(status=ExtractionStatus.COMPLETED, method=method, provider=" + ".join(providers))
        else:
            extraction = ExtractionInfo(
                status=ExtractionStatus.FAILED,
                method=ExtractionMethod.NONE,
                error="The complaint could not be processed automatically. Nothing was guessed. "
                "Please try again or enter the details yourself",
            )

        metadata: dict[str, str | int | float | bool | None] = {
            "language_detection": language.method.value,
            "extraction_method": extraction.method.value,
            "extraction_provider": extraction.provider,
            "extraction_prompt": EXTRACTION_PROMPT_VERSION if ai_ok else None,
            "translation_provider": translation.provider,
            "speech_to_text_provider": transcript.provider if transcript else None,
            "rejected_fact_count": len(rejected),
        }
        draft = IntakeResult(
            **common,
            status=ComplaintStatus.CREATED,
            intake_status=IntakeStatus.FAILED,
            translation=translation,
            extracted=extracted,
            rejected_facts=rejected,
            extraction=extraction,
            provider_metadata=metadata,
            provider_trace=trace,
            citizen_confirmation_status=ConfirmationStatus.NOT_READY,
        )
        return self._finalise(draft)
