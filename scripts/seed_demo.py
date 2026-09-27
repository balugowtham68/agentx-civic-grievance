"""Demo seeder for Hackathon MVP."""

import asyncio
import os
import sys

# Ensure backend can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../backend")))

from datetime import datetime, timedelta, UTC
from sqlalchemy import select
from app.database import Database
from app.core.config import get_settings
from app.models import Complaint
from app.schemas.enums import ComplaintStatus, InputChannel, AuthorityStatus
from app.schemas.complaint import SLAStateRead
from app.schemas.enums import SLAStage

async def seed_demo():
    settings = get_settings()
    db = Database(settings.database_url)
    
    with db.session() as session:
        print("Creating demo complaint in FILED state (approaching SLA)...")
        now = datetime.now(UTC)
        
        complaint = Complaint(
            tracking_id="AGX-2026-DEMO1",
            citizen_input="Engal theruvil moondru naatkalaaga street light velai seyyavillai.",
            input_channel=InputChannel.TEXT,
            language="te", # or ta for Tamil, based on registry
            status=ComplaintStatus.MONITORING,
            authority_status=AuthorityStatus.NONE,
            issue="Streetlight not working",
            category="streetlight",
            department_id="electrical",
            jurisdiction_id="zone-1",
            created_at=now - timedelta(minutes=10),
            updated_at=now - timedelta(minutes=2)
        )
        
        from app.models.complaint import SLARecord
        
        # Manually create an SLA that is approaching
        started_at = now - timedelta(minutes=15)
        complaint.sla = SLARecord(
            complaint_id=complaint.id,
            policy_id="sla-streetlight",
            started_at=started_at,
            warning_at=started_at + timedelta(minutes=8),
            deadline_at=started_at + timedelta(minutes=12),
            stage=SLAStage.ON_TRACK
        )
        
        session.add(complaint)
        session.commit()
        
        print(f"Created complaint with tracking ID {complaint.tracking_id}!")
        print("Wait for Watchdog to poll, or run:")
        print(f"curl -X POST http://127.0.0.1:8000/api/v1/watchdog/run")

if __name__ == "__main__":
    asyncio.run(seed_demo())
