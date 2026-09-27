"""LanguageFusionService: Fuses multi-source signals into a high-confidence decision."""

from __future__ import annotations

from app.core.languages import LanguageRegistry
from app.core.logging import get_logger
from app.services.ai.provider import AIProvider
from app.services.language_detection.lexical_marker import LexicalMarkerAnalyzer
from app.services.language_detection.llm_verifier import LLMLanguageVerifier
from app.services.language_detection.ngram_classifier import NgramLanguageClassifier
from app.services.language_detection.schemas import (
    AudioSignal,
    ConfidenceTier,
    DetectionSignals,
    LanguageDetectRequest,
    LanguageDetectResponse,
)
from app.services.language_detection.script_analyzer import ScriptAnalyzer

logger = get_logger(__name__)

# Configurable confidence thresholds (as required by specification)
HIGH_CONFIDENCE_THRESHOLD = 0.85
MEDIUM_CONFIDENCE_THRESHOLD = 0.65

LANGUAGE_DISPLAY_NAMES = {
    "te": "Telugu",
    "ta": "Tamil",
    "kn": "Kannada",
    "hi": "Hindi",
    "ml": "Malayalam",
    "en": "English",
    "und": "Unknown",
}


class LanguageFusionService:
    """Reconciles Audio LID, Unicode Script, Lexical Markers, N-grams, and LLM verification."""

    def __init__(
        self,
        ai_provider: AIProvider | None = None,
        registry: LanguageRegistry | None = None,
    ) -> None:
        self.script_analyzer = ScriptAnalyzer()
        self.lexical_analyzer = LexicalMarkerAnalyzer()
        self.ngram_classifier = NgramLanguageClassifier()
        self.llm_verifier = LLMLanguageVerifier(ai_provider)
        self.registry = registry

    async def detect(self, request: LanguageDetectRequest) -> LanguageDetectResponse:
        text = request.text.strip()
        if not text:
            return LanguageDetectResponse(
                language=None,
                language_name="Unknown",
                confidence=0.0,
                confidence_tier="LOW",
                needs_confirmation=True,
                method="empty",
                reason_code="EMPTY_INPUT",
                signals=DetectionSignals(),
            )

        # 1. Audio Signal (if voice input was provided)
        audio_sig = None
        if request.audio_language:
            audio_sig = AudioSignal(
                language=request.audio_language,
                confidence=request.audio_confidence or 0.85,
                source=request.audio_source or "audio",
            )

        # 2. Script Analysis (Unicode block identification & code-mixing)
        script_sig = self.script_analyzer.analyze(text)

        # 3. Lexical Marker Analysis (Native + Romanized function words & loanword discount)
        lexical_sig = self.lexical_analyzer.analyze(text)

        # 4. N-gram Character & Subword Probability Classifier
        ngram_sig = self.ngram_classifier.predict(text)

        signals = DetectionSignals(
            audio=audio_sig,
            script=script_sig,
            lexical=lexical_sig,
            classifier=ngram_sig,
            llm=None,
        )

        # -------------------------------------------------------------
        # Decision Fusion Pipeline
        # -------------------------------------------------------------

        # CASE A: Strong Indic Script Presence (> 40% characters in an Indian script)
        if script_sig.script_language and script_sig.script_language != "en":
            indic_lang = script_sig.script_language
            # Check length: very short utterances (< 8 chars, e.g. "లైట్ లేదు")
            is_very_short = len(text) < 8
            base_conf = 0.96 if not is_very_short else 0.88

            # If code-mixed with English words (e.g. "మా street లో light పని చేయడం లేదు"),
            # it is STILL unambiguously Telugu/Indic because the grammar and script are native.
            if script_sig.is_code_mixed:
                base_conf = max(0.91, base_conf - 0.03)

            return self._build_response(
                language=indic_lang,
                confidence=base_conf,
                method="script_fusion",
                reason_code="DOMINANT_INDIC_SCRIPT",
                signals=signals,
            )

        # CASE B: Text is Latin Script (English OR Romanized Indian Language)
        # Check lexical markers for Romanized Indic languages
        lexical_lang = lexical_sig.language
        ngram_lang = ngram_sig.predicted_language
        ngram_conf = ngram_sig.confidence

        # If lexical markers strongly point to a Romanized Indian language
        if lexical_lang and lexical_lang != "en" and lexical_sig.confidence >= 0.70:
            final_lang = lexical_lang
            # Agreement between lexical and n-gram boosts confidence
            if ngram_lang == lexical_lang:
                fused_conf = min(0.96, lexical_sig.confidence + 0.15)
            else:
                fused_conf = lexical_sig.confidence

            # If confident enough (>= HIGH_CONFIDENCE_THRESHOLD), return
            if fused_conf >= HIGH_CONFIDENCE_THRESHOLD:
                return self._build_response(
                    language=final_lang,
                    confidence=fused_conf,
                    method="lexical_ngram_fusion",
                    reason_code="STRONG_ROMANIZED_INDIC_MARKERS",
                    signals=signals,
                )

        # CASE C: Ambiguous, Low Confidence, or Short Utterance in Latin Script
        # Verify with LLM if available
        llm_sig = None
        if self.llm_verifier.available:
            llm_sig = await self.llm_verifier.verify(
                text=text,
                candidate_probs=ngram_sig.probabilities,
                audio_hint=audio_sig.language if audio_sig else None,
            )
            signals.llm = llm_sig

        if llm_sig and llm_sig.executed and llm_sig.language:
            # Reconcile LLM with local signals
            llm_lang = llm_sig.language
            llm_conf = llm_sig.confidence

            # Agreement boost
            if llm_lang in (lexical_lang, ngram_lang, audio_sig.language if audio_sig else None):
                reconciled_conf = min(0.98, max(llm_conf, 0.90))
                reason = "LLM_AND_LOCAL_SIGNAL_AGREEMENT"
            else:
                # LLM disagreed with local candidate
                reconciled_conf = max(0.68, llm_conf * 0.85)
                reason = "LLM_VERIFIED_DISAGREEMENT"

            return self._build_response(
                language=llm_lang,
                confidence=reconciled_conf,
                method="llm_fusion",
                reason_code=reason,
                signals=signals,
            )

        # CASE D: Pure English Grammatical Utterance
        # If true English grammatical markers exist and heavily outweigh any accidental Indic homophones
        en_score = lexical_sig.marker_scores.get("en", 0)
        max_indic_score = max(lexical_sig.marker_scores.get(lang, 0) for lang in ("te", "ta", "kn", "hi", "ml"))
        if (en_score >= 3 and en_score > max_indic_score * 2) or (en_score >= 2 and max_indic_score == 0):
            return self._build_response(
                language="en",
                confidence=min(0.96, 0.82 + 0.03 * en_score),
                method="lexical_english",
                reason_code="ENGLISH_GRAMMAR_CONFIRMED",
                signals=signals,
            )

        # CASE E: Audio Signal Fallback (if voice recognition passed audio LID)
        if audio_sig and audio_sig.language and (audio_sig.confidence or 0.0) >= 0.70:
            return self._build_response(
                language=audio_sig.language,
                confidence=round(audio_sig.confidence or 0.75, 2),
                method="audio_lid_fallback",
                reason_code="AUDIO_LANGUAGE_SIGNAL",
                signals=signals,
            )

        # CASE F: N-gram Top Prediction
        if ngram_lang and ngram_conf >= 0.60:
            return self._build_response(
                language=ngram_lang,
                confidence=ngram_conf,
                method="ngram_prediction",
                reason_code="NGRAM_DISTRIBUTION_LEAD",
                signals=signals,
            )

        # CASE G: Truly Uncertain / Ambiguous
        return self._build_response(
            language=None,
            confidence=0.45,
            method="undetermined",
            reason_code="INSUFFICIENT_MULTI_SIGNAL_EVIDENCE",
            signals=signals,
        )

    def _build_response(
        self,
        language: str | None,
        confidence: float,
        method: str,
        reason_code: str,
        signals: DetectionSignals,
    ) -> LanguageDetectResponse:
        confidence = round(max(0.0, min(1.0, confidence)), 3)

        if confidence >= HIGH_CONFIDENCE_THRESHOLD and language:
            tier: ConfidenceTier = "HIGH"
            needs_confirmation = False
        elif confidence >= MEDIUM_CONFIDENCE_THRESHOLD and language:
            tier = "MEDIUM"
            needs_confirmation = True
        else:
            tier = "LOW"
            needs_confirmation = True

        name = LANGUAGE_DISPLAY_NAMES.get(language or "und", "Unknown")

        return LanguageDetectResponse(
            language=language,
            language_name=name,
            confidence=confidence,
            confidence_tier=tier,
            needs_confirmation=needs_confirmation,
            method=method,
            reason_code=reason_code,
            signals=signals,
        )
