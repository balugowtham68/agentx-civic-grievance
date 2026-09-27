"""Complaint endpoints (Phase 1: create raw complaint, read, status, audit).

The full UNDERSTAND -> ... -> EXPLAIN pipeline is attached to these resources in
later phases (e.g. POST /complaints/{id}/confirm in Phase 4/5).
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Query, Request, status
from pydantic import BaseModel, Field

from app.api.deps import AuditServiceDep, ComplaintServiceDep
from app.api.params import ComplaintId, TrackingId
from app.core.errors import ErrorResponse
from app.schemas.audit import AuditEventListResponse, AuditEventRead
from app.schemas.complaint import (
    ComplaintCreateRequest,
    ComplaintListResponse,
    ComplaintRead,
    ComplaintStatusResponse,
    ComplaintSummary,
)
from app.schemas.enums import ComplaintStatus, InputChannel

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
def get_complaint(complaint_id: ComplaintId, service: ComplaintServiceDep) -> ComplaintRead:
    return ComplaintRead.model_validate(service.get(complaint_id))


@router.get(
    "/complaints/{complaint_id}/status",
    response_model=ComplaintStatusResponse,
    responses={404: _errors[404]},
)
def get_complaint_status(complaint_id: ComplaintId, service: ComplaintServiceDep) -> ComplaintStatusResponse:
    return service.status(complaint_id)


@router.get(
    "/complaints/{complaint_id}/audit",
    response_model=AuditEventListResponse,
    responses={404: _errors[404]},
)
def get_complaint_audit(
    complaint_id: ComplaintId,
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
def track(tracking_id: TrackingId, service: ComplaintServiceDep) -> ComplaintStatusResponse:
    """Citizen tracking by mock-government tracking ID (IDs exist from Phase 5)."""
    return service.status(service.get_by_tracking_id(tracking_id).id)


@router.post(
    "/complaints/{complaint_id}/file",
    response_model=ComplaintRead,
    responses={404: _errors[404]},
)
def file_complaint(complaint_id: ComplaintId, service: ComplaintServiceDep) -> ComplaintRead:
    """Transitions complaint to FILED and ensures tracking ID is present."""
    complaint = service.get(complaint_id)
    if not complaint.tracking_id:
        complaint.tracking_id = f"SPN-{complaint.id[:6].upper()}"
    complaint.status = ComplaintStatus.FILED
    return ComplaintRead.model_validate(complaint)


class ConfirmDraftRequest(BaseModel):
    confirmed: bool = True
    edited_text: str | None = None


@router.post(
    "/complaints/{complaint_id}/confirm-draft",
    response_model=dict,
    responses={404: _errors[404]},
)
async def confirm_draft_endpoint(
    complaint_id: ComplaintId,
    body: ConfirmDraftRequest,
    request: Request,
) -> dict:
    """Citizen confirms the drafted civic grievance petition to proceed with official municipal authority filing."""
    worker = getattr(request.app.state, "pipeline_worker", None)
    if not worker:
        raise HTTPException(status_code=500, detail="Pipeline worker not initialized")
    return await worker.confirm_and_file(complaint_id, edited_body=body.edited_text)


from datetime import UTC, datetime
from app.core.events import get_event_bus, get_job_queue, DomainEvent, EventType, Job
from app.services.civic_validator import CivicValidationResult, validate_civic_intent
from app.services.notification import get_notification_service


class FastSubmissionRequest(BaseModel):
    text: str = Field(min_length=1)
    language: str | None = None
    location: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    channel: str = "text"
    photo_data: str | None = None
    photo_name: str | None = None
    diagnostic_details: dict[str, Any] | None = None


class ValidateIntentRequest(BaseModel):
    text: str
    language: str | None = None


FastSubmissionRequest.model_rebuild()
ValidateIntentRequest.model_rebuild()


class FastSubmissionResponse(BaseModel):
    complaint_id: str
    tracking_id: str
    status: str
    message: str
    created_at: datetime


@router.post(
    "/complaints/validate-intent",
    response_model=CivicValidationResult,
)
def validate_intent_endpoint(body: ValidateIntentRequest) -> CivicValidationResult:
    """Validates citizen input for civic relevance and returns diagnostic questions."""
    return validate_civic_intent(body.text, language=body.language)


@router.post(
    "/complaints/submit",
    response_model=FastSubmissionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def submit_complaint_fast(
    body: FastSubmissionRequest,
    service: ComplaintServiceDep,
) -> FastSubmissionResponse:
    """Fast Acknowledgement API (< 500ms): verifies civic intent, registers grievance,
    assigns SPN-XXXXXX tracking ID, and delegates deep AI processing to background workers."""
    # 1. Civic Intent & Nonsense Validation
    val = validate_civic_intent(body.text, language=body.language)
    if not val.is_civic:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=val.message or "This does not appear to be a municipal civic grievance. Please describe a civic problem like broken streetlights, water supply, potholes, or garbage.",
        )

    # 2. Mandatory Live GPS validation
    if body.latitude is None or body.longitude is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Live GPS location is mandatory for grievance verification. Please share your live location.",
        )

    # 3. Mandatory Photo Proof validation
    if not body.photo_data and not body.photo_name:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Photo proof is mandatory for municipal inspection. Please attach a photo of the civic issue.",
        )

    # 4. Enrich grievance input with diagnostic details if citizen provided them
    citizen_text = body.text
    if body.diagnostic_details:
        diag_lines = [f"{k}: {v}" for k, v in body.diagnostic_details.items() if v]
        if diag_lines:
            citizen_text += f"\n[Specifics: {', '.join(diag_lines)}]"

    complaint = service.create(
        ComplaintCreateRequest(
            citizen_input=citizen_text,
            language=body.language,
            channel=InputChannel.VOICE if body.channel == "voice" else InputChannel.TEXT,
        )
    )

    # Assign memorable tracking ID
    tracking_id = f"SPN-{complaint.id[:6].upper()}"
    complaint.tracking_id = tracking_id
    if body.location:
        complaint.location = body.location

    # Record citizen timeline: Initial acknowledgement
    notifier = get_notification_service()
    notifier.record_timeline(
        complaint.id,
        stage="RECEIVED",
        message=f"Complaint received. Tracking ID {tracking_id} assigned.",
        details={"tracking_id": tracking_id, "channel": body.channel},
        icon="inbox",
    )

    # Record GPS coordinates in timeline if shared
    if body.latitude is not None and body.longitude is not None:
        notifier.record_timeline(
            complaint.id,
            stage="GPS_LOCATED",
            message=f"Live GPS coordinates captured ({body.latitude:.5f}° N, {body.longitude:.5f}° E).",
            details={"latitude": body.latitude, "longitude": body.longitude},
            icon="crosshair",
        )

    # Record photo evidence in timeline if attached
    if body.photo_data or body.photo_name:
        notifier.record_timeline(
            complaint.id,
            stage="EVIDENCE_VERIFIED",
            message=f"Photographic proof attached ({body.photo_name or '1 image'}). Geotagged for municipal inspection.",
            details={"photo_attached": True, "photo_name": body.photo_name},
            icon="camera",
        )

    # Commit session so background worker can immediately read the complaint
    service.repo.session.commit()

    # Enqueue background processing job & emit domain event
    job_queue = get_job_queue()
    await job_queue.enqueue(
        Job(
            job_type="process_complaint",
            complaint_id=complaint.id,
            payload={
                "location": body.location,
                "latitude": body.latitude,
                "longitude": body.longitude,
                "language": body.language,
                "category_hint": val.category,
            },
            idempotency_key=f"submit:{complaint.id}",
        )
    )

    event_bus = get_event_bus()
    await event_bus.publish(
        DomainEvent(
            event_type=EventType.COMPLAINT_CREATED,
            complaint_id=complaint.id,
            payload={"tracking_id": tracking_id},
        )
    )

    return FastSubmissionResponse(
        complaint_id=complaint.id,
        tracking_id=tracking_id,
        status="RECEIVED",
        message="Your complaint has been received. SPANDAN AI is processing it in the background.",
        created_at=complaint.created_at,
    )


@router.get("/complaints/{complaint_id}/timeline")
def get_complaint_timeline(complaint_id: ComplaintId, service: ComplaintServiceDep):
    """Returns the asynchronous processing timeline for citizen transparency."""
    complaint = service.get(complaint_id)
    notifier = get_notification_service()
    entries = notifier.get_timeline(complaint_id)
    return {
        "complaint_id": complaint.id,
        "tracking_id": complaint.tracking_id,
        "status": complaint.status.value,
        "issue": complaint.issue,
        "location": complaint.location,
        "department_id": complaint.department_id,
        "jurisdiction_id": complaint.jurisdiction_id,
        "timeline": [e.model_dump() for e in entries],
    }


class LocationConfirmRequest(BaseModel):
    confirmed: bool = True
    corrected_location: str | None = None


@router.post("/complaints/{complaint_id}/location/confirm")
def confirm_complaint_location(
    complaint_id: ComplaintId,
    body: LocationConfirmRequest,
    service: ComplaintServiceDep,
):
    """Citizen confirms or updates their resolved location."""
    complaint = service.get(complaint_id)
    if body.corrected_location:
        complaint.location = body.corrected_location
    notifier = get_notification_service()
    notifier.record_timeline(
        complaint_id,
        stage="LOCATION_CONFIRMED",
        message=f"Location confirmed by citizen as '{complaint.location}'.",
        icon="map-pin",
    )
    return {"complaint_id": complaint_id, "location": complaint.location, "confirmed": True}


@router.get("/location/reverse")
async def reverse_geocode_location(
    lat: Annotated[float, Query(ge=-90, le=90)],
    lng: Annotated[float, Query(ge=-180, le=180)],
):
    """Reverse geocodes latitude/longitude into human-readable civic address and municipal ward."""
    from app.services.location.resolver import LocalCivicResolver
    from app.services.location.schemas import LocationInput

    resolver = LocalCivicResolver()
    res = await resolver.resolve(LocationInput(latitude=lat, longitude=lng))
    return {
        "latitude": lat,
        "longitude": lng,
        "formatted_address": res.formatted_address or f"GPS: {lat:.5f}° N, {lng:.5f}° E",
        "locality": res.locality,
        "ward": res.ward,
        "city": res.city,
        "state": res.state,
        "jurisdiction_id": res.jurisdiction_id,
    }


