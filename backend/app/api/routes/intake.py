"""Citizen intake endpoints (Phase 2, UNDERSTAND stage).

Routes only translate HTTP to IntakeService calls. All intake paths live under
/intake/... (the early /complaints/{id}/intake/... aliases were removed during the
Phase 1-4 consolidation; the frontend uses the canonical paths).
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query, Request, status

from app.api.deps import IntakeServiceDep, SettingsDep
from app.api.params import ComplaintId
from app.core.errors import ErrorResponse, PayloadTooLargeError
from app.schemas.complaint import LANGUAGE_CODE_PATTERN
from app.schemas.intake import (
    ClarificationAnswerRequest,
    IntakeCapabilities,
    IntakeCorrectionRequest,
    IntakeHandoff,
    IntakeRerunRequest,
    IntakeResult,
    TextIntakeRequest,
)

router = APIRouter(tags=["intake"])


def _errors(*codes: int) -> dict[int | str, dict[str, object]]:
    return {code: {"model": ErrorResponse} for code in codes}


@router.get("/intake/capabilities", response_model=IntakeCapabilities)
def intake_capabilities(service: IntakeServiceDep) -> IntakeCapabilities:
    """Languages with honest support levels, and which providers are available (offline first)."""
    return service.capabilities()


@router.post("/intake/text", response_model=IntakeResult, status_code=status.HTTP_201_CREATED, responses=_errors(422))
async def intake_text(body: TextIntakeRequest, service: IntakeServiceDep) -> IntakeResult:
    """Create a complaint from the citizen's text (or browser-transcribed speech) and understand it offline.

    Works with no network and no API key. If understanding fails, the complaint is still
    saved with intake_status FAILED and nothing is guessed.
    """
    return await service.submit_text(body)


@router.post(
    "/intake/voice",
    response_model=IntakeResult,
    status_code=status.HTTP_201_CREATED,
    responses=_errors(413, 415, 422, 502, 503, 504),
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {
                t: {"schema": {"type": "string", "format": "binary"}}
                for t in ("audio/webm", "audio/ogg", "audio/wav", "audio/mpeg", "audio/mp4")
            },
        }
    },
)
async def intake_voice(
    request: Request,
    service: IntakeServiceDep,
    settings: SettingsDep,
    language: Annotated[str | None, Query(pattern=LANGUAGE_CODE_PATTERN)] = None,
) -> IntakeResult:
    """Upload a recording as the raw body (Content-Type: audio/*). Server speech-to-text is
    local first (if a local model is installed), then optional remote; otherwise 503 and the
    citizen uses browser speech recognition or types. Audio is never stored."""
    limit = settings.max_audio_bytes
    declared = request.headers.get("content-length")
    if declared and declared.isdigit() and int(declared) > limit:
        raise PayloadTooLargeError(f"Audio is larger than the {limit // (1024 * 1024)} MB limit")
    chunks: list[bytes] = []
    size = 0
    async for chunk in request.stream():
        size += len(chunk)
        if size > limit:
            raise PayloadTooLargeError(f"Audio is larger than the {limit // (1024 * 1024)} MB limit")
        chunks.append(chunk)
    return await service.submit_voice(b"".join(chunks), request.headers.get("content-type"), language)


# ---------------------------------------------------------------- per complaint (canonical)


@router.get("/intake/{complaint_id}", response_model=IntakeResult, responses=_errors(404))
def get_intake(complaint_id: ComplaintId, service: IntakeServiceDep) -> IntakeResult:
    return service.get_result(complaint_id)


@router.post("/intake/{complaint_id}/process", response_model=IntakeResult, responses=_errors(404, 409, 422))
async def process_intake(
    complaint_id: ComplaintId, service: IntakeServiceDep, body: IntakeRerunRequest | None = None
) -> IntakeResult:
    """Run (or retry) intake for a complaint still in CREATED, optionally with a chosen language."""
    return await service.process(complaint_id, body.language if body else None)


@router.post("/intake/{complaint_id}/answer", response_model=IntakeResult, responses=_errors(404, 409, 422))
async def answer_clarification(complaint_id: ComplaintId, body: ClarificationAnswerRequest, service: IntakeServiceDep) -> IntakeResult:
    """Citizen answers a clarification question; facts are re-extracted from all their statements."""
    return await service.answer(complaint_id, body.text)


@router.post("/intake/{complaint_id}/correction", response_model=IntakeResult, responses=_errors(404, 409, 422))
def correct_intake(complaint_id: ComplaintId, body: IntakeCorrectionRequest, service: IntakeServiceDep) -> IntakeResult:
    """Citizen corrects facts: structured `corrections`, or their own words in `text`
    ("No, it is 5 days"), parsed offline. Attributed to the citizen; newest wins."""
    return service.correct(complaint_id, body)


@router.post("/intake/{complaint_id}/confirm", response_model=IntakeResult, responses=_errors(404, 409))
def confirm_intake(complaint_id: ComplaintId, service: IntakeServiceDep) -> IntakeResult:
    """Citizen confirms "What I understood". The only way a complaint becomes UNDERSTOOD."""
    return service.confirm(complaint_id)


@router.get("/intake/{complaint_id}/handoff", response_model=IntakeHandoff, responses=_errors(404, 409))
def intake_handoff(complaint_id: ComplaintId, service: IntakeServiceDep) -> IntakeHandoff:
    """The confirmed intake as Phase 3 will consume it. 409 until the citizen confirms."""
    return service.handoff(complaint_id)
