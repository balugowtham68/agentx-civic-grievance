"""API routes for Municipal Authority Review and Higher Official Escalation."""

from __future__ import annotations

from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session

from app.api.deps import DatabaseDep, get_session
from app.core.clock import get_clock
from app.core.errors import InvalidStateTransitionError
from app.core.logging import get_logger
from app.core.state_machine import ensure_transition
from app.models.complaint import Complaint
from app.schemas.audit import AuditEventCreate
from app.schemas.enums import ActorType, AuditEventType, AuthorityStatus, ComplaintStatus
from app.services.audit_service import AuditService
from app.services.notification.email_service import demo_email_service

logger = get_logger(__name__)

router = APIRouter(prefix="/review", tags=["Authority Review & Escalation"])


def _find_complaint(session: Session, identifier: str) -> Complaint:
    """Finds complaint by UUID or tracking ID."""
    complaint = session.get(Complaint, identifier)
    if not complaint:
        complaint = session.query(Complaint).filter(Complaint.tracking_id == identifier).first()
    if not complaint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Complaint with ID or tracking ID '{identifier}' was not found.",
        )
    return complaint


def _render_portal_html(
    title: str,
    badge_text: str,
    badge_color: str,
    heading: str,
    description: str,
    complaint: Complaint,
    additional_notes: str | None = None,
    secondary_action_url: str | None = None,
    secondary_action_label: str | None = None,
) -> str:
    """Renders a polished, official government administrative feedback page."""
    tracking_id = complaint.tracking_id or complaint.id[:8].upper()
    category = complaint.category or "Civic Infrastructure"
    issue = complaint.issue or complaint.citizen_input[:80]
    location = complaint.location or "Verified Locality"
    dept = complaint.department_id or "GHMC Municipal Corporation"
    status_val = complaint.status.value

    sec_btn = ""
    if secondary_action_url and secondary_action_label:
        sec_btn = f"""<div style="margin-top: 24px; text-align: center;">
            <a href="{secondary_action_url}" style="display:inline-block; padding: 12px 24px; background: #0f172a; color: white; text-decoration: none; border-radius: 8px; font-weight: 700; font-size: 14px;">
              {secondary_action_label}
            </a>
          </div>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title} — SPANDAN AI Civic Redressal</title>
  <style>
    body {{
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
      background: #0f172a;
      color: #1e293b;
      margin: 0;
      padding: 32px 16px;
      display: flex;
      justify-content: center;
      align-items: center;
      min-height: 100vh;
      box-sizing: border-box;
    }}
    .card {{
      background: #ffffff;
      border-radius: 20px;
      max-width: 620px;
      width: 100%;
      overflow: hidden;
      box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
    }}
    .top-bar {{
      background: #1e293b;
      color: #94a3b8;
      padding: 16px 28px;
      font-size: 12px;
      font-weight: 700;
      letter-spacing: 1px;
      text-transform: uppercase;
      display: flex;
      justify-content: space-between;
      align-items: center;
      border-bottom: 1px solid #334155;
    }}
    .body {{
      padding: 36px 32px;
    }}
    .badge {{
      display: inline-block;
      padding: 6px 14px;
      background: {badge_color}15;
      color: {badge_color};
      border: 1px solid {badge_color}40;
      border-radius: 9999px;
      font-size: 13px;
      font-weight: 800;
      letter-spacing: 0.5px;
      margin-bottom: 20px;
    }}
    h1 {{
      margin: 0 0 12px 0;
      font-size: 24px;
      font-weight: 800;
      color: #0f172a;
      letter-spacing: -0.5px;
    }}
    p.lead {{
      margin: 0 0 24px 0;
      font-size: 15px;
      line-height: 1.6;
      color: #475569;
    }}
    .details-box {{
      background: #f8fafc;
      border: 1px solid #e2e8f0;
      border-radius: 14px;
      padding: 20px;
      margin-bottom: 24px;
      font-size: 14px;
      line-height: 1.7;
    }}
    .details-box div {{
      margin-bottom: 6px;
    }}
    .details-box div strong {{
      color: #0f172a;
      display: inline-block;
      min-width: 140px;
    }}
    .notes {{
      background: #f1f5f9;
      border-left: 4px solid {badge_color};
      padding: 14px 18px;
      border-radius: 0 8px 8px 0;
      font-size: 13px;
      color: #334155;
      line-height: 1.5;
    }}
    .footer {{
      background: #f8fafc;
      padding: 18px 32px;
      border-top: 1px solid #e2e8f0;
      font-size: 12px;
      color: #64748b;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }}
  </style>
</head>
<body>
  <div class="card">
    <div class="top-bar">
      <span>SPANDAN AI Municipal Portal</span>
      <span>Official Record</span>
    </div>
    <div class="body">
      <div class="badge">{badge_text}</div>
      <h1>{heading}</h1>
      <p class="lead">{description}</p>
      
      <div class="details-box">
        <div><strong>Tracking ID:</strong> <span style="font-family: monospace; font-weight: bold; color: #0284c7;">{tracking_id}</span></div>
        <div><strong>Current Lifecycle Status:</strong> <span style="font-weight: 800; color: {badge_color};">{status_val}</span></div>
        <div><strong>Category:</strong> {category}</div>
        <div><strong>Issue Details:</strong> {issue}</div>
        <div><strong>Incident Location:</strong> {location}</div>
        <div><strong>Civic Department:</strong> {dept}</div>
      </div>

      {f'<div class="notes">{additional_notes}</div>' if additional_notes else ''}
      {sec_btn}
    </div>
    <div class="footer">
      <span>Autonomous Grievance Dispatch System</span>
      <span>G.O. Ms. No. 2026-GHMC</span>
    </div>
  </div>
</body>
</html>"""


@router.get("/{identifier}/accept")
@router.post("/{identifier}/accept")
def authority_accept_complaint(
    identifier: str,
    request: Request,
    session: Session = Depends(get_session),
) -> Any:
    """Workflow Step 2: Authority clicks ACCEPT -> ACCEPTED_BY_AUTHORITY."""
    clock = get_clock()
    complaint = _find_complaint(session, identifier)

    # Transition to ACCEPTED_BY_AUTHORITY
    if complaint.status != ComplaintStatus.ACCEPTED_BY_AUTHORITY:
        ensure_transition(complaint.status, ComplaintStatus.ACCEPTED_BY_AUTHORITY)
        complaint.status = ComplaintStatus.ACCEPTED_BY_AUTHORITY
        complaint.authority_status = AuthorityStatus.ACKNOWLEDGED
        complaint.updated_at = clock.now()

        audit = AuditService(session, clock)
        audit.record(
            AuditEventCreate(
                complaint_id=complaint.id,
                event_type=AuditEventType.AUTHORITY_ACCEPTED,
                actor_type=ActorType.AUTHORITY,
                actor_name="Designated Municipal Reviewing Officer",
                summary=f"Complaint {complaint.tracking_id or complaint.id} officially ACCEPTED by Authority",
                payload={
                    "status": ComplaintStatus.ACCEPTED_BY_AUTHORITY.value,
                    "action": "ACCEPT",
                    "authority_status": AuthorityStatus.ACKNOWLEDGED.value,
                },
            )
        )
        session.commit()

    logger.info("Complaint accepted by authority", extra={"complaint_id": complaint.id, "status": complaint.status.value})

    if "application/json" in request.headers.get("accept", "") and "text/html" not in request.headers.get("accept", ""):
        return {
            "success": True,
            "complaint_id": complaint.id,
            "tracking_id": complaint.tracking_id,
            "status": complaint.status.value,
            "message": "Grievance accepted by municipal authority. Work scheduled under SLA monitoring.",
        }

    html = _render_portal_html(
        title="Grievance Accepted by Authority",
        badge_text="✓ OFFICIALLY ACCEPTED BY AUTHORITY",
        badge_color="#059669",
        heading="Grievance Accepted for Execution",
        description=f"Local authority has officially accepted grievance <strong>{complaint.tracking_id}</strong>. The repair and maintenance wing has been notified to execute resolution within the mandated SLA.",
        complaint=complaint,
        additional_notes="Administrative status updated to <code>ACCEPTED_BY_AUTHORITY</code>. Field execution teams have received work orders.",
    )
    return HTMLResponse(content=html, status_code=200)


@router.get("/{identifier}/reject")
@router.post("/{identifier}/reject")
def authority_reject_complaint(
    identifier: str,
    request: Request,
    session: Session = Depends(get_session),
) -> Any:
    """Workflow Step 3: Authority clicks REJECT -> REJECTED -> ESCALATED -> send escalation email to HIGHER_OFFICIAL_EMAIL."""
    clock = get_clock()
    complaint = _find_complaint(session, identifier)

    # 1. Transition to REJECTED then ESCALATED
    if complaint.status != ComplaintStatus.ESCALATED:
        # Move to REJECTED first
        ensure_transition(complaint.status, ComplaintStatus.REJECTED)
        complaint.status = ComplaintStatus.REJECTED
        complaint.updated_at = clock.now()

        audit = AuditService(session, clock)
        audit.record(
            AuditEventCreate(
                complaint_id=complaint.id,
                event_type=AuditEventType.AUTHORITY_REJECTED,
                actor_type=ActorType.AUTHORITY,
                actor_name="Designated Municipal Reviewing Officer",
                summary=f"Complaint {complaint.tracking_id or complaint.id} REJECTED by Authority",
                payload={"status": ComplaintStatus.REJECTED.value, "action": "REJECT"},
            )
        )

        # Move to ESCALATED
        ensure_transition(complaint.status, ComplaintStatus.ESCALATED)
        complaint.status = ComplaintStatus.ESCALATED
        complaint.updated_at = clock.now()

        audit.record(
            AuditEventCreate(
                complaint_id=complaint.id,
                event_type=AuditEventType.ESCALATION_TRIGGERED,
                actor_type=ActorType.SYSTEM,
                actor_name="AuthorityRejectionEscalator",
                summary=f"Complaint {complaint.tracking_id or complaint.id} ESCALATED to Higher Official following local rejection",
                payload={
                    "status": ComplaintStatus.ESCALATED.value,
                    "target_recipient": demo_email_service.get_higher_official_email(),
                },
            )
        )
        session.commit()

    # 2. Dispatch escalation email to HIGHER_OFFICIAL_EMAIL
    email_res = demo_email_service.send_higher_official_escalation_email(
        complaint,
        base_url=str(request.base_url),
    )
    logger.info(
        "Complaint rejected and escalated to higher official",
        extra={"complaint_id": complaint.id, "escalation_recipient": email_res.recipient},
    )

    if "application/json" in request.headers.get("accept", "") and "text/html" not in request.headers.get("accept", ""):
        return {
            "success": True,
            "complaint_id": complaint.id,
            "tracking_id": complaint.tracking_id,
            "status": complaint.status.value,
            "escalated_to": email_res.recipient,
            "higher_accept_url": email_res.action_urls.get("higher_accept"),
            "message": "Grievance rejected by local authority and automatically escalated to Higher Official.",
        }

    html = _render_portal_html(
        title="Grievance Rejected & Escalated",
        badge_text="⚠️ REJECTED & AUTOMATICALLY ESCALATED",
        badge_color="#dc2626",
        heading="Grievance Escalated to Higher Authority",
        description=f"Local authority has rejected grievance <strong>{complaint.tracking_id}</strong>. Per civic accountability guidelines, this grievance has been automatically <strong>ESCALATED</strong> to the Higher Official.",
        complaint=complaint,
        additional_notes=f"Escalation notification dispatched to Higher Official at <code>{email_res.recipient}</code>. Executive review is now pending.",
        secondary_action_url=email_res.action_urls.get("higher_accept"),
        secondary_action_label="Review as Higher Official & Accept Escalation &rarr;",
    )
    return HTMLResponse(content=html, status_code=200)


@router.get("/{identifier}/higher-accept")
@router.post("/{identifier}/higher-accept")
def higher_official_accept_complaint(
    identifier: str,
    request: Request,
    session: Session = Depends(get_session),
) -> Any:
    """Workflow Step 4: Higher official clicks ACCEPT -> ACCEPTED_BY_HIGHER_AUTHORITY."""
    clock = get_clock()
    complaint = _find_complaint(session, identifier)

    if complaint.status != ComplaintStatus.ACCEPTED_BY_HIGHER_AUTHORITY:
        ensure_transition(complaint.status, ComplaintStatus.ACCEPTED_BY_HIGHER_AUTHORITY)
        complaint.status = ComplaintStatus.ACCEPTED_BY_HIGHER_AUTHORITY
        complaint.authority_status = AuthorityStatus.IN_PROGRESS
        complaint.updated_at = clock.now()

        audit = AuditService(session, clock)
        audit.record(
            AuditEventCreate(
                complaint_id=complaint.id,
                event_type=AuditEventType.HIGHER_OFFICIAL_ACCEPTED,
                actor_type=ActorType.AUTHORITY,
                actor_name="Higher Grievance Authority / Principal Executive Official",
                summary=f"Complaint {complaint.tracking_id or complaint.id} ACCEPTED by Higher Official upon escalation",
                payload={
                    "status": ComplaintStatus.ACCEPTED_BY_HIGHER_AUTHORITY.value,
                    "action": "HIGHER_ACCEPT",
                    "authority_status": AuthorityStatus.IN_PROGRESS.value,
                },
            )
        )
        session.commit()

    logger.info("Complaint accepted by higher official", extra={"complaint_id": complaint.id, "status": complaint.status.value})

    if "application/json" in request.headers.get("accept", "") and "text/html" not in request.headers.get("accept", ""):
        return {
            "success": True,
            "complaint_id": complaint.id,
            "tracking_id": complaint.tracking_id,
            "status": complaint.status.value,
            "message": "Grievance officially accepted by Higher Authority. High-priority executive remediation engaged.",
        }

    html = _render_portal_html(
        title="Accepted by Higher Authority",
        badge_text="★ ACCEPTED BY HIGHER OFFICIAL",
        badge_color="#2563eb",
        heading="Executive Overrule & Acceptance",
        description=f"Grievance <strong>{complaint.tracking_id}</strong> has been officially accepted by the <strong>Higher Official</strong> following escalation. High-priority direct intervention is now active.",
        complaint=complaint,
        additional_notes="Administrative status updated to <code>ACCEPTED_BY_HIGHER_AUTHORITY</code>. Overrule directive issued to municipal engineering divisions.",
    )
    return HTMLResponse(content=html, status_code=200)


@router.get("/{identifier}/status")
def get_review_status(
    identifier: str,
    request: Request,
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    """Returns current review status and available action links for demo purposes."""
    complaint = _find_complaint(session, identifier)
    urls = demo_email_service.get_action_urls(complaint.id, base_url=str(request.base_url))

    return {
        "complaint_id": complaint.id,
        "tracking_id": complaint.tracking_id,
        "status": complaint.status.value,
        "authority_status": complaint.authority_status.value,
        "action_urls": urls,
        "can_authority_accept": complaint.status in {ComplaintStatus.FILED, ComplaintStatus.MONITORING, ComplaintStatus.CREATED},
        "can_authority_reject": complaint.status in {ComplaintStatus.FILED, ComplaintStatus.MONITORING, ComplaintStatus.CREATED},
        "can_higher_accept": complaint.status == ComplaintStatus.ESCALATED,
    }


@router.get("/mailbox")
def get_official_mailbox(
    session: Session = Depends(get_session),
) -> list[dict[str, Any]]:
    """Returns recent dispatched emails for Authority and Higher Official review."""
    from app.services.notification.service import notification_service
    records = [
        n for n in notification_service._notifications 
        if n.event_type in {"AUTHORITY_REVIEW_EMAIL", "HIGHER_OFFICIAL_ESCALATION_EMAIL"}
    ]
    results = []
    for r in reversed(records[-40:]):
        c = session.get(Complaint, r.complaint_id)
        results.append({
            "id": r.id,
            "complaint_id": r.complaint_id,
            "tracking_id": r.metadata.get("tracking_id", c.tracking_id if c else ""),
            "event_type": r.event_type,
            "recipient": r.metadata.get("recipient", ""),
            "title": r.title,
            "message": r.message,
            "created_at": r.created_at.isoformat(),
            "current_status": c.status.value if c else "UNKNOWN",
            "urls": r.metadata.get("urls", {}),
            "delivered": r.metadata.get("delivered", False),
            "issue": c.issue if c else "",
            "location": c.location if c else "",
            "category": c.category if c else "",
        })
    return results

