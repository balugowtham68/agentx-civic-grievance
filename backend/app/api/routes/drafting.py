"""Complaint drafting endpoints (Phase 4). Routes only translate HTTP to DraftingService calls."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Path, status

from app.api.deps import DraftingServiceDep
from app.api.params import ComplaintId
from app.core.errors import ErrorResponse
from app.schemas.drafting import (
    ComplaintDraft,
    DraftApproveRequest,
    DraftEditRequest,
    DraftRunRequest,
    DraftView,
)

router = APIRouter(prefix="/drafting", tags=["drafting"])



def _errors(*codes: int) -> dict[int | str, dict[str, object]]:
    return {code: {"model": ErrorResponse} for code in codes}


@router.post("/{complaint_id}/run", response_model=DraftView, status_code=status.HTTP_201_CREATED,
             responses=_errors(404, 409, 422))
async def run_drafting(complaint_id: ComplaintId, service: DraftingServiceDep, body: DraftRunRequest | None = None) -> DraftView:
    """Generate draft v1 for a CLASSIFIED complaint (409 for anything else). Nothing is filed."""
    return await service.run(complaint_id, body or DraftRunRequest())


@router.get("/{complaint_id}", response_model=DraftView, responses=_errors(404, 422))
def get_draft(complaint_id: ComplaintId, service: DraftingServiceDep) -> DraftView:
    """The current draft version and the version history."""
    return service.get(complaint_id)


@router.get("/{complaint_id}/versions/{version}", response_model=ComplaintDraft, responses=_errors(404, 422))
def get_draft_version(
    complaint_id: ComplaintId, version: Annotated[int, Path(ge=1, le=10_000)], service: DraftingServiceDep
) -> ComplaintDraft:
    return service.version(complaint_id, version)


@router.post("/{complaint_id}/edit", response_model=DraftView, responses=_errors(404, 409, 422))
def edit_draft(complaint_id: ComplaintId, body: DraftEditRequest, service: DraftingServiceDep) -> DraftView:
    """Citizen edits the wording; a new version is saved and earlier versions are kept."""
    return service.edit(complaint_id, body)


@router.post("/{complaint_id}/approve", response_model=DraftView, responses=_errors(404, 409, 422))
def approve_draft(complaint_id: ComplaintId, body: DraftApproveRequest, service: DraftingServiceDep) -> DraftView:
    """Citizen approves the latest version: complaint becomes DRAFTED. Filing is a later phase."""
    return service.approve(complaint_id, body)
