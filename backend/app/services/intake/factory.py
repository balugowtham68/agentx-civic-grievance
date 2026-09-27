"""Builds the Intake Agent and its providers from settings (one place for wiring)."""

from __future__ import annotations

import httpx

from app.agents.intake import IntakeAgent
from app.core.config import Settings
from app.core.languages import LanguageRegistry
from app.services.ai import build_ai_provider
from app.services.external import TranscriptionProvider
from app.services.intake.speech_to_text import (
    ChainTranscriptionProvider,
    GeminiTranscriptionProvider,
    LocalWhisperProvider,
    WhisperTranscriptionProvider,
)


def build_transcription_provider(
    settings: Settings, transport: httpx.AsyncBaseTransport | None = None
) -> TranscriptionProvider:
    """Multi-tiered transcription: local model, Gemini audio, or remote Whisper."""
    mode = settings.speech_to_text_provider
    providers: list[object] = []
    if mode in {"auto", "local"}:
        providers.append(LocalWhisperProvider(settings.local_stt_model_path))

    gemini_key = settings.secret("gemini_api_key")
    if gemini_key is not None:
        providers.append(
            GeminiTranscriptionProvider(
                gemini_key,
                model=settings.gemini_model,
                base_url=settings.gemini_base_url,
                timeout_seconds=settings.stt_timeout_seconds,
                transport=transport,
            )
        )

    openai_key = settings.secret("openai_api_key")
    if mode in {"auto", "whisper"} and openai_key is not None:
        providers.append(
            WhisperTranscriptionProvider(
                openai_key,
                model=settings.whisper_model,
                base_url=settings.whisper_base_url,
                timeout_seconds=settings.stt_timeout_seconds,
                transport=transport,
            )
        )
    return ChainTranscriptionProvider(providers)  # type: ignore[return-value]


def build_intake_agent(settings: Settings, registry: LanguageRegistry) -> IntakeAgent:
    return IntakeAgent(
        build_ai_provider(settings),
        transcription=build_transcription_provider(settings),
        registry=registry,
    )
