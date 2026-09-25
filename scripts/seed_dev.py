"""Create a couple of sample complaints in the local database for UI development.

Usage (from backend/):  python ../scripts/seed_dev.py
Only creates CREATED complaints - the Phase 1 foundation has no agent behaviour yet.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.core.config import get_settings  # noqa: E402
from app.database import Database  # noqa: E402
from app.schemas.complaint import ComplaintCreateRequest  # noqa: E402
from app.services.complaint_service import ComplaintService  # noqa: E402

SAMPLES = [
    ComplaintCreateRequest(
        citizen_input="మా ఇంటి దగ్గర రామాలయం పక్కన వీధి దీపం 5 రోజులుగా పనిచేయడం లేదు",
        language="te",
        channel="voice",
    ),
    ComplaintCreateRequest(
        citizen_input="Garbage has not been collected on Station Road for a week.",
        language="en",
    ),
]


def main() -> None:
    settings = get_settings()
    db = Database(settings.database_url)
    db.init_schema()
    with db.session() as session:
        service = ComplaintService(session)
        for sample in SAMPLES:
            complaint = service.create(sample)
            print(f"created {complaint.id}  status={complaint.status.value}")
    db.dispose()


if __name__ == "__main__":
    main()
