"""Complaint endpoints (Phase 1: create raw complaint, read, status, audit).

The full UNDERSTAND -> ... -> EXPLAIN pipeline is attached to these resources in
later phases (e.g. POST /complaints/{id}/confirm in Phase 4/5).
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query, status

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
    """Mock implementation: normally would invoke FilingAgent."""
    complaint = service.get(complaint_id)
    if complaint.status == ComplaintStatus.DRAFTED:
        complaint.status = ComplaintStatus.FILED
        complaint.tracking_id = complaint.tracking_id or f"SPN-{complaint.id[:6].upper()}"
    return ComplaintRead.model_validate(complaint)


from fastapi import BackgroundTasks, HTTPException, Request
from app.api.deps import DatabaseDep, ReferenceDep
from app.schemas.complaint import (
    ComplaintSubmitRequest,
    FastAckResponse,
    ProblemDetectRequest,
    ProblemDetectResponse,
    TimelineResponse,
    TimelineStage,
)
from app.services.workflow import AutonomousWorkflowPipeline
from app.services.location import (
    LocationConfirmRequest,
    LocationCorrectRequest,
    LocationResolution,
    location_resolver,
)


@router.post(
    "/complaints/detect-options",
    response_model=ProblemDetectResponse,
    responses={422: _errors[422]},
)
def detect_problem_and_options(
    body: ProblemDetectRequest,
    db: DatabaseDep,
) -> ProblemDetectResponse:
    """Compares citizen data with PostgreSQL database, identifies problem-related options,
    and drafts formal grievance for citizen confirmation."""
    from app.services.civic_validator import validate_civic_complaint
    from app.services.problem_matcher import compare_and_detect_problem

    # 1. Nonsense & Gibberish Validation
    is_valid, error_reason = validate_civic_complaint(body.text)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=error_reason or "Your complaint description appears invalid. Please describe an actual civic problem.",
        )

    # 2. Mandatory Live GPS Location Validation
    if body.latitude is None or body.longitude is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Live GPS location (latitude and longitude) is mandatory for problem detection and options matching.",
        )

    # 3. Mandatory Photo Proof Validation
    if not body.photo_data or not body.photo_data.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Photo proof is mandatory for verifying the problem and generating the official draft.",
        )

    # 4. Compare with PostgreSQL and extract problem options & draft
    with db.session() as session:
        return compare_and_detect_problem(
            session=session,
            text_input=body.text,
            language=body.language,
            latitude=body.latitude,
            longitude=body.longitude,
            location_str=body.location,
            photo_data=body.photo_data,
        )


@router.post(
    "/complaints/submit",
    response_model=FastAckResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses={422: _errors[422]},
)
async def submit_complaint_fast_ack(
    body: ComplaintSubmitRequest,
    service: ComplaintServiceDep,
    db: DatabaseDep,
    reference: ReferenceDep,
    request: Request,
    background_tasks: BackgroundTasks,
) -> FastAckResponse:
    """Fast acknowledgement endpoint: enforces mandatory live GPS and photo proof,
    persists confirmed drafting details, and enqueues autonomous AI pipeline."""
    from uuid import uuid4
    from app.schemas.complaint import ComplaintCreateRequest
    from app.services.civic_validator import validate_civic_complaint

    # 1. Nonsense & Gibberish Validation
    is_valid, error_reason = validate_civic_complaint(body.text)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=error_reason or "Your complaint description appears to be invalid or uninformative. Please describe a genuine civic problem.",
        )

    # 2. Mandatory Live GPS Location Validation
    if body.latitude is None or body.longitude is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Live GPS location (latitude and longitude) is mandatory for registering a civic complaint. Please enable GPS location on your device or click 'Use Current Location'.",
        )

    # 3. Mandatory Photo Proof Validation
    if not body.photo_data or not body.photo_data.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Photo proof is mandatory for registering a civic complaint. Please capture or upload a clear photo of the civic issue.",
        )

    # Resolve location from GPS coordinates
    resolved_loc = location_resolver.resolve(latitude=body.latitude, longitude=body.longitude, source="GPS")
    location_str = resolved_loc.summary() if resolved_loc else (body.location or f"GPS: {body.latitude:.4f}, {body.longitude:.4f}")
    tracking_id = f"SPN-{uuid4().hex[:6].upper()}"

    draft_initial = {
        "photo_proof": body.photo_data,
        "gps": {"latitude": body.latitude, "longitude": body.longitude},
        "location_summary": location_str,
        "confirmed_category": body.confirmed_category,
        "confirmed_department": body.confirmed_department,
        "title": body.draft_subject or f"Grievance: {body.text[:60]}",
        "subject": body.draft_subject or f"Grievance: {body.text[:60]}",
        "body": body.draft_body or body.text,
        "citizen_confirmed_draft": True,
    }

    complaint = service.create(
        ComplaintCreateRequest(
            citizen_input=body.text,
            language=body.language,
            channel=body.channel,
        ),
        tracking_id=tracking_id,
        location=location_str,
        drafted_complaint=draft_initial,
    )
    if body.confirmed_category:
        complaint.category = body.confirmed_category
    if body.confirmed_department:
        complaint.department_id = body.confirmed_department
    if body.draft_subject:
        complaint.issue = body.draft_subject

    service.session.commit()

    # Workflow Step 1: Send review email to AUTHORITY_REVIEW_EMAIL
    from app.services.notification.email_service import demo_email_service
    demo_email_service.send_authority_review_email(complaint, base_url=str(request.base_url))

    # Launch autonomous processing pipeline in background
    pipeline = AutonomousWorkflowPipeline(db, reference)
    background_tasks.add_task(pipeline.process, complaint.id, app_state=request.app.state)

    return FastAckResponse(
        complaint_id=complaint.id,
        tracking_id=tracking_id,
        status="RECEIVED",
        message="Your confirmed grievance with GPS verification and photo proof has been lodged. SPANDAN AI is processing it in the background.",
        created_at=complaint.created_at,
        has_photo_proof=True,
        location_summary=location_str,
    )


@router.get(
    "/complaints/{complaint_id}/timeline",
    response_model=TimelineResponse,
    responses={404: _errors[404]},
)
def get_complaint_timeline(
    complaint_id: str,
    service: ComplaintServiceDep,
) -> TimelineResponse:
    """Returns citizen-friendly timeline and status stages for a complaint."""
    try:
        complaint = service.get(complaint_id)
    except Exception:
        # Try finding by tracking ID if UUID lookup fails
        complaint = service.get_by_tracking_id(complaint_id)

    stages_def = [
        ("RECEIVED", "Complaint Received", "Citizen grievance received with GPS and photo proof."),
        ("UNDERSTOOD", "Language & Facts Extracted", "AI extracted issue facts, duration, and locality."),
        ("CLASSIFIED", "Responsible Department Identified", f"Assigned to {complaint.department_id or 'Municipal Department'} ({complaint.jurisdiction_id or 'Civic Authority'})."),
        ("DRAFTED", "Formal Grievance Drafted", "Administrative bilingual complaint prepared and verified."),
        ("FILED", "Filed with Civic Authority", "Official grievance registered with tracking receipt."),
        ("MONITORING", "SLA Monitoring Active", "Watchdog is continuously tracking resolution deadline."),
    ]

    status_order = [
        ComplaintStatus.CREATED,
        ComplaintStatus.UNDERSTOOD,
        ComplaintStatus.CLASSIFIED,
        ComplaintStatus.DRAFTED,
        ComplaintStatus.FILED,
        ComplaintStatus.MONITORING,
    ]

    current_idx = -1
    for i, s in enumerate(status_order):
        if complaint.status == s:
            current_idx = i
            break
    if complaint.status in (
        ComplaintStatus.WARNING,
        ComplaintStatus.BREACHED,
        ComplaintStatus.ESCALATED,
        ComplaintStatus.RESOLVED,
        ComplaintStatus.CLOSED,
        ComplaintStatus.ACCEPTED_BY_AUTHORITY,
        ComplaintStatus.REJECTED,
        ComplaintStatus.ACCEPTED_BY_HIGHER_AUTHORITY,
    ):
        current_idx = 5  # At or beyond monitoring

    timeline_stages: list[TimelineStage] = []
    for i, (stage_code, label, desc) in enumerate(stages_def):
        if i < current_idx:
            st = "COMPLETED"
        elif i == current_idx:
            st = "IN_PROGRESS"
        else:
            st = "PENDING"

        timeline_stages.append(
            TimelineStage(
                stage=stage_code,
                label=label,
                description=desc,
                timestamp=complaint.updated_at if i <= current_idx else None,
                status=st,
            )
        )

    deadline = complaint.sla.deadline_at if complaint.sla else None

    # Retrieve photo proof and GPS coordinates if present
    photo_url = None
    has_photo = False
    gps_coords = None
    if complaint.drafted_complaint and isinstance(complaint.drafted_complaint, dict):
        photo_url = complaint.drafted_complaint.get("photo_proof")
        has_photo = bool(photo_url)
        gps_raw = complaint.drafted_complaint.get("gps")
        if isinstance(gps_raw, dict):
            gps_coords = {
                "latitude": float(gps_raw.get("latitude", 0)),
                "longitude": float(gps_raw.get("longitude", 0)),
            }

    return TimelineResponse(
        complaint_id=complaint.id,
        tracking_id=complaint.tracking_id or f"SPN-{complaint.id[:6].upper()}",
        current_status=complaint.status,
        stages=timeline_stages,
        department=complaint.department_id,
        jurisdiction=complaint.jurisdiction_id,
        location=complaint.location,
        issue=complaint.issue,
        sla_deadline=deadline,
        photo_url=photo_url,
        has_photo_proof=has_photo,
        gps_coordinates=gps_coords,
    )


@router.post(
    "/complaints/{complaint_id}/location/confirm",
    response_model=ComplaintRead,
    responses={404: _errors[404]},
)
def confirm_location(
    complaint_id: str,
    body: LocationConfirmRequest,
    service: ComplaintServiceDep,
) -> ComplaintRead:
    complaint = service.get(complaint_id)
    if body.locality:
        complaint.location = body.locality
    return ComplaintRead.model_validate(complaint)


@router.post(
    "/complaints/{complaint_id}/location/correct",
    response_model=ComplaintRead,
    responses={404: _errors[404]},
)
def correct_location(
    complaint_id: str,
    body: LocationCorrectRequest,
    service: ComplaintServiceDep,
) -> ComplaintRead:
    complaint = service.get(complaint_id)
    parts = [p for p in [body.locality, body.ward, body.city, body.district, body.state] if p]
    if parts:
        complaint.location = ", ".join(parts)
    return ComplaintRead.model_validate(complaint)

