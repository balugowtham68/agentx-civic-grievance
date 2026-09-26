"""Interfaces for external integrations. Implementations arrive in later phases.

| Interface                 | Implemented in | Notes                                             |
| ------------------------- | -------------- | ------------------------------------------------- |
| MockGovernmentGrievanceAPI| Phase 5        | Hackathon mock only; never a real portal          |
| TranscriptionProvider     | Phase 2 (done) | Web Speech runs in browser; this is the server    |
|                           |                | path for uploaded audio (Whisper)                 |
| TranslationProvider       | Phase 2 (done) | Backed by AIProvider                              |
| LanguageDetector          | Phase 2 (done) | Script detection + AIProvider for Latin script    |
| KnowledgeRetriever        | Phase 3 (done) | ChromaDB over knowledge_base/, local embeddings   |
| EscalationNotifier        | Phase 8        | Hands an escalation to a human authority          |

Each is a Protocol so agents depend on the interface, and tests can pass fakes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from app.schemas.classification import RetrievedKnowledge
from app.schemas.mock_gov import (
    MockEscalationReceipt,
    MockEscalationRequest,
    MockGrievanceReceipt,
    MockGrievanceStatus,
    MockGrievanceSubmission,
)


class MockGovernmentGrievanceAPI(Protocol):
    async def submit_grievance(self, submission: MockGrievanceSubmission) -> MockGrievanceReceipt: ...

    async def get_status(self, tracking_id: str) -> MockGrievanceStatus: ...

    async def escalate(self, request: MockEscalationRequest) -> MockEscalationReceipt: ...


@dataclass(frozen=True)
class Transcript:
    text: str
    language: str | None
    provider: str
    confidence: float | None = None  # None unless the provider really reports one


class TranscriptionProvider(Protocol):
    """Speech-to-text for uploaded audio (Phase 2: app/services/intake/speech_to_text.py)."""

    name: str

    @property
    def available(self) -> bool: ...

    async def transcribe(
        self, audio: bytes, *, audio_format: str, language_hint: str | None = None
    ) -> Transcript: ...


# Name used in the Phase 2 specification.
SpeechToTextProvider = TranscriptionProvider


@dataclass(frozen=True)
class Translation:
    text: str
    source_language: str
    target_language: str
    provider: str


class TranslationProvider(Protocol):
    """Phase 2: app/services/intake/translation.py. Language detection moved to
    LanguageDetector so it can run without translation."""

    name: str

    @property
    def available(self) -> bool: ...

    async def translate(
        self, text: str, *, source_language: str, target_language: str
    ) -> Translation: ...


@dataclass(frozen=True)
class DetectedLanguage:
    language: str  # ISO code or "und"
    method: str  # declared | script | provider | default
    confidence: float | None = None
    transliterated: bool = False
    script: str | None = None


class LanguageDetector(Protocol):
    """Phase 2: app/services/intake/language_detection.py."""

    async def detect(self, text: str) -> DetectedLanguage: ...


class KnowledgeRetriever(Protocol):
    """Phase 3: app/services/knowledge/store.py (CivicKnowledgeBase)."""

    def retrieve(
        self, queries: list[str], *, top_k: int, where: dict[str, Any] | None = None, max_chars: int = 2000
    ) -> list[RetrievedKnowledge]: ...


class EscalationNotifier(Protocol):
    async def notify(self, *, authority_id: str, tracking_id: str, reason: str) -> None: ...
