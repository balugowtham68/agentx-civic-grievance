"""Diagnostic script to test live email delivery via SMTP."""

import sys
from pathlib import Path

# Add backend to path
BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import get_settings
from app.models.complaint import Complaint
from app.services.notification.email_service import demo_email_service

def test_delivery(custom_password: str | None = None):
    settings = get_settings()
    if custom_password:
        from pydantic import SecretStr
        settings.smtp_password = SecretStr(custom_password.strip())

    print("=" * 60)
    print("SPANDAN AI — LIVE EMAIL DELIVERY DIAGNOSTIC")
    print("=" * 60)
    print(f"SMTP Host:      {settings.smtp_host}:{settings.smtp_port}")
    print(f"Sender:         {settings.smtp_user}")
    print(f"Authority To:   {demo_email_service.get_authority_email()}")
    print(f"Higher Off. To: {demo_email_service.get_higher_official_email()}")
    print("-" * 60)

    # 1. Test Authority Review Email
    dummy = Complaint(
        id="live-test-01",
        tracking_id="SPN-TEST01",
        citizen_input="Testing live email delivery to authority reviewer",
        category="Road Damage",
        issue="Pothole near main road",
        location="Cyber Towers, Madhapur",
        department_id="GHMC_ROADS",
    )

    print("\n[1/2] Sending Authority Review Email...")
    res1 = demo_email_service.send_authority_review_email(dummy)
    if res1.delivered:
        print(f"  >>> SUCCESS! Email delivered to {res1.recipient}")
    else:
        print(f"  >>> FAILED: {res1.delivery_error}")

    # 2. Test Higher Official Escalation Email
    print("\n[2/2] Sending Higher Official Escalation Email...")
    res2 = demo_email_service.send_higher_official_escalation_email(dummy)
    if res2.delivered:
        print(f"  >>> SUCCESS! Email delivered to {res2.recipient}")
    else:
        print(f"  >>> FAILED: {res2.delivery_error}")

    print("\n" + "=" * 60)

if __name__ == "__main__":
    pwd = sys.argv[1] if len(sys.argv) > 1 else None
    test_delivery(pwd)
