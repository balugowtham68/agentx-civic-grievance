"""LLM Verification layer for ambiguous or low-confidence language detection."""

from __future__ import annotations

from pydantic import BaseModel, Field
from app.core.logging import get_logger
from app.services.ai.provider import AIProvider, PromptSpec
from app.services.language_detection.schemas import LLMVerificationSignal

logger = get_logger(__name__)

SUPPORTED_CODES = ["te", "ta", "kn", "hi", "en", "ml", "und"]


class LLMStructuredLanguageOutput(BaseModel):
    language: str = Field(description="ISO 639-1 code: te, ta, kn, hi, en, ml, or und if truly unknown")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence in range 0.0 to 1.0")
    reason_code: str = Field(description="Short reason code e.g. TELUGU_GRAMMAR, ROMANIZED_INDIC, CODE_MIXED, SHORT_PHRASE")


class LLMLanguageVerifier:
    """Uses the configured AIProvider to verify ambiguous or Romanized civic language utterances."""

    def __init__(self, ai_provider: AIProvider | None = None) -> None:
        self._ai = ai_provider

    @property
    def available(self) -> bool:
        return self._ai is not None and self._ai.available

    async def verify(
        self,
        text: str,
        candidate_probs: dict[str, float] | None = None,
        audio_hint: str | None = None,
    ) -> LLMVerificationSignal:
        if not self.available:
            return LLMVerificationSignal(executed=False)

        system_instruction = (
            "You are a specialized linguistic language identifier for Indian civic grievances.\n"
            "Analyze the text carefully. Pay close attention to Romanized Indian languages\n"
            "(e.g., 'maa street lo light pani cheyyatledu' is Telugu with English loanwords, NOT English).\n"
            "Code-switching where English technical terms ('street light', 'water meter', 'drainage')\n"
            "are embedded in Indian grammar should be identified as the underlying Indian language.\n"
            "Supported languages: te (Telugu), ta (Tamil), kn (Kannada), hi (Hindi), en (English), ml (Malayalam).\n"
            "If undetermined, answer 'und'."
        )

        candidates_str = ", ".join(f"{k}: {v:.2f}" for k, v in (candidate_probs or {}).items())
        user_prompt = (
            f"Citizen Text: {text}\n"
            f"Classifier Candidates: {candidates_str}\n"
            f"Audio Hint: {audio_hint or 'None'}\n\n"
            "Identify the true primary language."
        )

        spec = PromptSpec(
            name="language_detection.llm_verify",
            version="v1.0",
            system=system_instruction,
            user=user_prompt,
        )

        try:
            result = await self._ai.generate_structured(spec, LLMStructuredLanguageOutput)
            lang = result.language.strip().lower()
            if lang not in SUPPORTED_CODES:
                lang = "und"
            return LLMVerificationSignal(
                language=lang if lang != "und" else None,
                confidence=round(result.confidence, 3),
                reason_code=result.reason_code,
                executed=True,
            )
        except Exception as exc:
            logger.warning("LLM language verification failed, falling back to deterministic signals", extra={"error": str(exc)})
            return LLMVerificationSignal(executed=False)
