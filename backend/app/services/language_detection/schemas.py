"""Schemas for the Multi-Signal Language Identification System (SPANDAN AI)."""

from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, Field

ConfidenceTier = Literal["HIGH", "MEDIUM", "LOW"]


class AudioSignal(BaseModel):
    language: str | None = None
    confidence: float | None = None
    source: str = "audio"


class ScriptSignal(BaseModel):
    dominant_script: str | None = None
    script_language: str | None = None
    native_char_ratio: float = 0.0
    latin_char_ratio: float = 0.0
    is_code_mixed: bool = False


class LexicalSignal(BaseModel):
    language: str | None = None
    confidence: float = 0.0
    marker_scores: dict[str, int] = Field(default_factory=dict)
    matched_markers: list[str] = Field(default_factory=list)
    english_loanword_count: int = 0


class NgramClassifierSignal(BaseModel):
    predicted_language: str | None = None
    confidence: float = 0.0
    probabilities: dict[str, float] = Field(default_factory=dict)


class LLMVerificationSignal(BaseModel):
    language: str | None = None
    confidence: float = 0.0
    reason_code: str | None = None
    executed: bool = False


class DetectionSignals(BaseModel):
    audio: AudioSignal | None = None
    script: ScriptSignal | None = None
    lexical: LexicalSignal | None = None
    classifier: NgramClassifierSignal | None = None
    llm: LLMVerificationSignal | None = None


class LanguageDetectRequest(BaseModel):
    text: str
    audio_language: str | None = None
    audio_confidence: float | None = None
    audio_source: str | None = None
    user_hint: str | None = None


class LanguageDetectResponse(BaseModel):
    language: str | None
    language_name: str
    confidence: float
    confidence_tier: ConfidenceTier
    needs_confirmation: bool
    method: str
    reason_code: str
    signals: DetectionSignals
