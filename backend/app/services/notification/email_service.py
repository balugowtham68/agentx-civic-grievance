"""Email notification service for Authority Review & Higher Official Escalation."""

from __future__ import annotations

import email.utils
from email.header import Header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib
from typing import Any
from dataclasses import dataclass, field

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.complaint import Complaint
from app.services.notification.service import notification_service

logger = get_logger(__name__)


@dataclass
class EmailDispatchResult:
    recipient: str
    subject: str
    action_type: str
    delivered: bool
    delivery_error: str | None = None
    action_urls: dict[str, str] = field(default_factory=dict)


class DemoEmailService:
    """Manages email dispatch for hackathon authority review and higher-official escalation."""

    def __init__(self) -> None:
        self.settings = get_settings()

    def get_authority_email(self) -> str:
        """Returns the configured authority review recipient email."""
        raw = self.settings.authority_review_email or "authority@example.gov.in"
        # If user entered username without domain, append @gmail.com
        if "@" not in raw:
            return f"{raw}@gmail.com"
        return raw.strip()

    def get_higher_official_email(self) -> str:
        """Returns the configured higher official recipient email."""
        raw = self.settings.higher_official_email or "higher.official@example.gov.in"
        if "@" not in raw:
            return f"{raw}@gmail.com"
        return raw.strip()

    def get_base_url(self, override_url: str | None = None) -> str:
        base = override_url or self.settings.app_base_url or "http://localhost:8000"
        return base.rstrip("/")

    def get_action_urls(self, complaint_id_or_tracking: str, base_url: str | None = None) -> dict[str, str]:
        base = self.get_base_url(base_url)
        return {
            "accept": f"{base}/api/v1/review/{complaint_id_or_tracking}/accept",
            "reject": f"{base}/api/v1/review/{complaint_id_or_tracking}/reject",
            "higher_accept": f"{base}/api/v1/review/{complaint_id_or_tracking}/higher-accept",
            "status": f"{base}/api/v1/review/{complaint_id_or_tracking}/status",
        }

    def send_authority_review_email(
        self,
        complaint: Complaint,
        base_url: str | None = None,
    ) -> EmailDispatchResult:
        """Sends review email to AUTHORITY_REVIEW_EMAIL with ACCEPT and REJECT action links."""
        recipient = self.get_authority_email()
        tracking_id = complaint.tracking_id or complaint.id[:8].upper()
        urls = self.get_action_urls(complaint.id, base_url)
        subject = f"[CIVIC REVIEW REQUIRED] New Grievance {tracking_id}: {complaint.category or 'Citizen Complaint'}"

        location_str = complaint.location or "Verified Locality"
        issue_str = complaint.issue or complaint.citizen_input[:100]
        dept_str = complaint.department_id or "GHMC Municipal Corporation"

        # HTML Email Template
        html_body = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f8fafc; margin: 0; padding: 24px; color: #1e293b; }}
    .container {{ max-width: 640px; margin: 0 auto; background: #ffffff; border-radius: 16px; border: 1px solid #e2e8f0; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); }}
    .header {{ background: #0f172a; padding: 24px; color: #ffffff; text-align: center; }}
    .header h1 {{ margin: 0; font-size: 20px; font-weight: 800; letter-spacing: -0.5px; }}
    .header p {{ margin: 4px 0 0 0; font-size: 13px; color: #94a3b8; }}
    .content {{ padding: 28px; }}
    .badge {{ display: inline-block; padding: 4px 10px; background: #dbeafe; color: #1e40af; border-radius: 9999px; font-size: 12px; font-weight: 700; margin-bottom: 16px; }}
    .card {{ background: #f1f5f9; border-radius: 12px; padding: 18px; margin-bottom: 24px; font-size: 14px; line-height: 1.6; }}
    .field {{ margin-bottom: 10px; }}
    .field strong {{ color: #334155; }}
    .actions {{ display: flex; gap: 12px; margin-top: 28px; text-align: center; }}
    .btn-accept {{ display: inline-block; padding: 14px 28px; background: #059669; color: #ffffff !important; text-decoration: none; border-radius: 10px; font-weight: 700; font-size: 14px; box-shadow: 0 2px 4px rgba(5,150,105,0.2); }}
    .btn-reject {{ display: inline-block; padding: 14px 28px; background: #dc2626; color: #ffffff !important; text-decoration: none; border-radius: 10px; font-weight: 700; font-size: 14px; box-shadow: 0 2px 4px rgba(220,38,38,0.2); }}
    .footer {{ padding: 20px 28px; background: #f8fafc; border-top: 1px solid #e2e8f0; font-size: 12px; color: #64748b; text-align: center; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>MUNICIPAL GRIEVANCE REVIEW PORTAL</h1>
      <p>SPANDAN AI — Autonomous Civic Grievance System</p>
    </div>
    <div class="content">
      <span class="badge">ACTION REQUIRED BY LOCAL AUTHORITY</span>
      <h2 style="margin: 0 0 16px 0; font-size: 18px; color: #0f172a;">Grievance Lodgement: {tracking_id}</h2>
      
      <div class="card">
        <div class="field"><strong>Tracking ID:</strong> {tracking_id}</div>
        <div class="field"><strong>Category:</strong> {complaint.category or 'General Civic Problem'}</div>
        <div class="field"><strong>Subject:</strong> {issue_str}</div>
        <div class="field"><strong>Citizen Statement:</strong> "{complaint.citizen_input}"</div>
        <div class="field"><strong>Location:</strong> {location_str}</div>
        <div class="field"><strong>Assigned Department:</strong> {dept_str}</div>
        <div class="field"><strong>Verification:</strong> Mandatory Live GPS & Photo Proof Verified</div>
      </div>

      <p style="font-size: 14px; font-weight: 600; color: #334155; margin-bottom: 8px;">
        Please review the facts and choose an action:
      </p>

      <div class="actions">
        <a href="{urls['accept']}" class="btn-accept">✓ ACCEPT COMPLAINT</a>
        &nbsp;&nbsp;
        <a href="{urls['reject']}" class="btn-reject">✗ REJECT COMPLAINT</a>
      </div>

      <p style="font-size: 12px; color: #64748b; margin-top: 24px; line-height: 1.5;">
        <em>Note:</em> Clicking <strong>ACCEPT</strong> will mark the complaint as <code>ACCEPTED_BY_AUTHORITY</code> and schedule civic works.
        Clicking <strong>REJECT</strong> will mark the complaint as <code>REJECTED</code>, automatically trigger <code>ESCALATED</code>, and notify the Higher Official for executive intervention.
      </p>
    </div>
    <div class="footer">
      SPANDAN AI Civic Redressal Engine &bull; Automated Dispatch to {recipient}
    </div>
  </div>
</body>
</html>"""

        plain_text = f"""MUNICIPAL GRIEVANCE REVIEW REQUIRED
-----------------------------------
Tracking ID: {tracking_id}
Category: {complaint.category or 'Civic Problem'}
Subject: {issue_str}
Location: {location_str}
Citizen Statement: {complaint.citizen_input}
Assigned Department: {dept_str}

ACTIONS:
To ACCEPT complaint: {urls['accept']}
To REJECT complaint: {urls['reject']}
"""

        delivered, error = self._dispatch_smtp(recipient, subject, html_body, plain_text)

        # Record in in-app notification store
        notification_service.notify(
            complaint_id=complaint.id,
            event_type="AUTHORITY_REVIEW_EMAIL",
            channel="EMAIL",
            title=f"Review Email Dispatched ({tracking_id})",
            message=f"Review email dispatched to authority at {recipient}. Accept URL: {urls['accept']}",
            metadata={
                "recipient": recipient,
                "tracking_id": tracking_id,
                "urls": urls,
                "delivered": delivered,
            },
        )

        return EmailDispatchResult(
            recipient=recipient,
            subject=subject,
            action_type="AUTHORITY_REVIEW",
            delivered=delivered,
            delivery_error=error,
            action_urls=urls,
        )

    def send_higher_official_escalation_email(
        self,
        complaint: Complaint,
        base_url: str | None = None,
    ) -> EmailDispatchResult:
        """Sends escalation email to HIGHER_OFFICIAL_EMAIL with ACCEPT action link."""
        recipient = self.get_higher_official_email()
        tracking_id = complaint.tracking_id or complaint.id[:8].upper()
        urls = self.get_action_urls(complaint.id, base_url)
        subject = f"[ESCALATION] Grievance {tracking_id} REJECTED by Local Authority — Executive Review Required"

        location_str = complaint.location or "Verified Locality"
        issue_str = complaint.issue or complaint.citizen_input[:100]
        dept_str = complaint.department_id or "GHMC Municipal Corporation"

        html_body = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f8fafc; margin: 0; padding: 24px; color: #1e293b; }}
    .container {{ max-width: 640px; margin: 0 auto; background: #ffffff; border-radius: 16px; border: 1px solid #fecdd3; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); }}
    .header {{ background: #991b1b; padding: 24px; color: #ffffff; text-align: center; }}
    .header h1 {{ margin: 0; font-size: 20px; font-weight: 800; letter-spacing: -0.5px; }}
    .header p {{ margin: 4px 0 0 0; font-size: 13px; color: #fecdd3; }}
    .content {{ padding: 28px; }}
    .alert-banner {{ background: #fff1f2; border: 1px solid #f43f5e; border-radius: 10px; padding: 14px 18px; margin-bottom: 20px; font-size: 14px; font-weight: 700; color: #9f1239; }}
    .card {{ background: #f8fafc; border-radius: 12px; padding: 18px; margin-bottom: 24px; font-size: 14px; line-height: 1.6; border: 1px solid #e2e8f0; }}
    .field {{ margin-bottom: 10px; }}
    .field strong {{ color: #334155; }}
    .btn-higher-accept {{ display: inline-block; padding: 14px 32px; background: #1d4ed8; color: #ffffff !important; text-decoration: none; border-radius: 10px; font-weight: 800; font-size: 15px; box-shadow: 0 4px 6px rgba(29,78,216,0.25); }}
    .footer {{ padding: 20px 28px; background: #f8fafc; border-top: 1px solid #e2e8f0; font-size: 12px; color: #64748b; text-align: center; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>EXECUTIVE CIVIC ESCALATION</h1>
      <p>Higher Municipal & State Grievance Authority</p>
    </div>
    <div class="content">
      <div class="alert-banner">
        ⚠️ LOCAL AUTHORITY REJECTION — ESCALATED TO HIGHER OFFICIAL
      </div>
      <h2 style="margin: 0 0 16px 0; font-size: 18px; color: #0f172a;">Escalated Grievance: {tracking_id}</h2>

      <div class="card">
        <div class="field"><strong>Tracking ID:</strong> {tracking_id}</div>
        <div class="field"><strong>Current Status:</strong> <span style="color:#b91c1c; font-weight:bold;">REJECTED &rarr; ESCALATED</span></div>
        <div class="field"><strong>Category:</strong> {complaint.category or 'Civic Hazard'}</div>
        <div class="field"><strong>Issue Description:</strong> {issue_str}</div>
        <div class="field"><strong>Citizen Statement:</strong> "{complaint.citizen_input}"</div>
        <div class="field"><strong>Location:</strong> {location_str}</div>
        <div class="field"><strong>Original Department:</strong> {dept_str}</div>
        <div class="field"><strong>Reason for Escalation:</strong> Local authority declined intervention. Executive review requested under civic accountability protocol.</div>
      </div>

      <p style="font-size: 14px; font-weight: 600; color: #334155; margin-bottom: 12px;">
        As the Higher Official, review the incident and click below to override and accept under direct executive supervision:
      </p>

      <div style="text-align: center; margin: 24px 0;">
        <a href="{urls['higher_accept']}" class="btn-higher-accept">✓ ACCEPT ESCALATED COMPLAINT</a>
      </div>

      <p style="font-size: 12px; color: #64748b; line-height: 1.5;">
        <em>Note:</em> Clicking <strong>ACCEPT</strong> will immediately transition the complaint to <code>ACCEPTED_BY_HIGHER_AUTHORITY</code>, bypassing local level delays and dispatching executive enforcement.
      </p>
    </div>
    <div class="footer">
      SPANDAN AI Executive Escalation Protocol &bull; Dispatched to {recipient}
    </div>
  </div>
</body>
</html>"""

        plain_text = f"""EXECUTIVE ESCALATION REQUIRED
-----------------------------------
Tracking ID: {tracking_id}
Status: REJECTED by Local Authority -> ESCALATED
Category: {complaint.category or 'Civic Hazard'}
Subject: {issue_str}
Location: {location_str}
Citizen Statement: {complaint.citizen_input}

To ACCEPT under Higher Authority oversight:
{urls['higher_accept']}
"""

        delivered, error = self._dispatch_smtp(recipient, subject, html_body, plain_text)

        notification_service.notify(
            complaint_id=complaint.id,
            event_type="HIGHER_OFFICIAL_ESCALATION_EMAIL",
            channel="EMAIL",
            title=f"Escalation Dispatched to Higher Official ({tracking_id})",
            message=f"Escalation email sent to {recipient}. Higher Accept URL: {urls['higher_accept']}",
            metadata={
                "recipient": recipient,
                "tracking_id": tracking_id,
                "urls": urls,
                "delivered": delivered,
            },
        )

        return EmailDispatchResult(
            recipient=recipient,
            subject=subject,
            action_type="HIGHER_OFFICIAL_ESCALATION",
            delivered=delivered,
            delivery_error=error,
            action_urls=urls,
        )

    def _dispatch_smtp(
        self,
        recipient: str,
        subject: str,
        html_body: str,
        plain_text: str,
    ) -> tuple[bool, str | None]:
        smtp_user = self.settings.smtp_user
        if smtp_user and "@" not in smtp_user:
            smtp_user = f"{smtp_user.strip()}@gmail.com"
        elif smtp_user:
            smtp_user = smtp_user.strip()

        smtp_pass = self.settings.secret("smtp_password") if self.settings.smtp_password else None
        if smtp_pass:
            smtp_pass = smtp_pass.replace(" ", "").strip()

        from_email = self.settings.smtp_from_email or smtp_user or "spandan-ai@civic-portal.gov.in"
        if from_email and "@" not in from_email:
            from_email = f"{from_email.strip()}@gmail.com"
        elif from_email:
            from_email = from_email.strip()
        smtp_host = self.settings.smtp_host or "smtp.gmail.com"
        smtp_port = self.settings.smtp_port or 587

        msg = MIMEMultipart("alternative")
        msg["Subject"] = Header(subject, "utf-8")
        msg["From"] = email.utils.formataddr(("SPANDAN AI Civic Grievance", from_email))
        msg["To"] = recipient
        msg["Date"] = email.utils.formatdate(localtime=True)

        msg.attach(MIMEText(plain_text, "plain", "utf-8"))
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        if not smtp_user or not smtp_pass:
            logger.info(
                "SMTP credentials not fully provided; generated review email mock-delivered to outbox",
                extra={"recipient": recipient, "subject": subject},
            )
            return False, "SMTP credentials not configured (mock delivered)"

        try:
            with smtplib.SMTP(smtp_host, smtp_port, timeout=8) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(smtp_user, smtp_pass)
                server.sendmail(from_email, [recipient], msg.as_string())
            logger.info("Email delivered successfully via SMTP", extra={"recipient": recipient, "subject": subject})
            return True, None
        except Exception as exc:
            error_msg = f"{type(exc).__name__}: {exc}"
            logger.warning(
                "SMTP dispatch failed; fallback to web action links",
                extra={"recipient": recipient, "error": error_msg},
            )
            return False, error_msg


# Global singleton instance
demo_email_service = DemoEmailService()
