"""Interfaces for external integrations. Implementations arrive in later phases.

| Interface                 | Implemented in | Notes                                             |
| ------------------------- | -------------- | ------------------------------------------------- |
| MockGovernmentGrievanceAPI| Phase 5        | Hackathon mock only; never a real portal          |
| TranscriptionProvider     | Phase 2        | Web Speech runs in browser; this is the server    |
|                           |                | fallback (e.g. Whisper) for uploaded audio        |
| TranslationProvider       | Phase 2        | Likely backed by AIProvider                       |
| KnowledgeRetriever        | Phase 3        | ChromaDB over knowledge_base/                     |
| EscalationNotifier        | Phase 8        | Hands an escalation to a human authority          |

Each is a Protocol so agents depend on the interface, and tests can pass fakes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.schemas.agents import Evidence
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
    language: str
    confidence: float | None = None


class TranscriptionProvider(Protocol):
    async def transcribe(self, audio: bytes, *, language_hint: str | None = None) -> Transcript: ...


@dataclass(frozen=True)
class Translation:
    text: str
    source_language: str
    target_language: str


class TranslationProvider(Protocol):
    async def detect_language(self, text: str) -> str: ...

    async def translate(self, text: str, *, target_language: str) -> Translation: ...


class KnowledgeRetriever(Protocol):
    async def retrieve(self, query: str, *, top_k: int = 5) -> list[Evidence]: ...


class EscalationNotifier(Protocol):
    async def notify(self, *, authority_id: str, tracking_id: str, reason: str) -> None: ...
