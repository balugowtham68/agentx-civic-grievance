"""Complaint endpoints (Phase 1: create raw complaint, read, status, audit).

The full UNDERSTAND -> ... -> EXPLAIN pipeline is attached to these resources in
later phases (e.g. POST /complaints/{id}/confirm in Phase 4/5).
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query, status

from app.api.deps import AuditServiceDep, ComplaintServiceDep
from app.core.errors import ErrorResponse
from app.schemas.audit import AuditEventListResponse, AuditEventRead
from app.schemas.complaint import (
    ComplaintCreateRequest,
    ComplaintListResponse,
    ComplaintRead,
    ComplaintStatusResponse,
    ComplaintSummary,
)
from app.schemas.enums import ComplaintStatus

router = APIRouter(tags=["complaints"])

_errors = {
    404: {"model": ErrorResponse, "description": "Not found"},
    422: {"model": ErrorResponse, "description": "Validation error"},
}


@router.post(
    "/complaints",
    response_model=ComplaintRead,
    status_code=status.HTTP_201_CREATED,
    responses={422: _errors[422]},
)
def create_complaint(body: ComplaintCreateRequest, service: ComplaintServiceDep) -> ComplaintRead:
    """Record a citizen grievance as received (status CREATED)."""
    return ComplaintRead.model_validate(service.create(body))


@router.get("/complaints", response_model=ComplaintListResponse)
def list_complaints(
    service: ComplaintServiceDep,
    status_filter: Annotated[list[ComplaintStatus] | None, Query(alias="status")] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ComplaintListResponse:
    items, total = service.list(
        statuses=set(status_filter) if status_filter else None, limit=limit, offset=offset
    )
    return ComplaintListResponse(
        items=[ComplaintSummary.model_validate(c) for c in items], total=total
    )


@router.get("/complaints/{complaint_id}", response_model=ComplaintRead, responses={404: _errors[404]})
def get_complaint(complaint_id: str, service: ComplaintServiceDep) -> ComplaintRead:
    return ComplaintRead.model_validate(service.get(complaint_id))


@router.get(
    "/complaints/{complaint_id}/status",
    response_model=ComplaintStatusResponse,
    responses={404: _errors[404]},
)
def get_complaint_status(complaint_id: str, service: ComplaintServiceDep) -> ComplaintStatusResponse:
    return service.status(complaint_id)


@router.get(
    "/complaints/{complaint_id}/audit",
    response_model=AuditEventListResponse,
    responses={404: _errors[404]},
)
def get_complaint_audit(
    complaint_id: str,
    complaints: ComplaintServiceDep,
    audit: AuditServiceDep,
    limit: Annotated[int, Query(ge=1, le=500)] = 200,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> AuditEventListResponse:
    complaints.get(complaint_id)  # 404 if unknown
    items, total = audit.list_for_complaint(complaint_id, limit=limit, offset=offset)
    return AuditEventListResponse(items=[AuditEventRead.model_validate(e) for e in items], total=total)


@router.get(
    "/track/{tracking_id}", response_model=ComplaintStatusResponse, responses={404: _errors[404]}
)
def track(tracking_id: str, service: ComplaintServiceDep) -> ComplaintStatusResponse:
    """Citizen tracking by mock-government tracking ID (IDs exist from Phase 5)."""
    return service.status(service.get_by_tracking_id(tracking_id).id)
