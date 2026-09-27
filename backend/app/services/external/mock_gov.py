from __future__ import annotations

import random
from datetime import datetime, timezone
from typing import Literal

from app.core.clock import Clock, get_clock
from app.schemas.enums import AuthorityStatus
from app.schemas.mock_gov import (
    MockAuthorityUpdate,
    MockEscalationReceipt,
    MockEscalationRequest,
    MockGrievanceReceipt,
    MockGrievanceStatus,
    MockGrievanceSubmission,
)
from app.services.external.interfaces import MockGovernmentGrievanceAPI


class InMemoryMockGovernmentAPI(MockGovernmentGrievanceAPI):
    """In-memory mock for the Government API. Discards state on restart."""

    def __init__(self, clock: Clock | None = None) -> None:
        self.clock = clock or get_clock()
        self._grievances: dict[str, MockGrievanceStatus] = {}
        self._escalations: dict[str, MockEscalationReceipt] = {}

    def _generate_tracking_id(self) -> str:
        return f"CIV-{self.clock.now().year}-{random.randint(10000, 99999)}"

    async def submit_grievance(self, submission: MockGrievanceSubmission) -> MockGrievanceReceipt:
        tracking_id = self._generate_tracking_id()
        now = self.clock.now()

        # Save initial state
        self._grievances[tracking_id] = MockGrievanceStatus(
            tracking_id=tracking_id,
            status=AuthorityStatus.RECEIVED,
            updates=[
                MockAuthorityUpdate(
                    status=AuthorityStatus.RECEIVED,
                    actor="System",
                    note="Complaint received",
                    at=now,
                )
            ],
            simulation=True,
        )

        return MockGrievanceReceipt(
            tracking_id=tracking_id,
            received_at=now,
            status=AuthorityStatus.RECEIVED,
            simulation=True,
        )

    async def get_status(self, tracking_id: str) -> MockGrievanceStatus:
        if tracking_id not in self._grievances:
            return MockGrievanceStatus(
                tracking_id=tracking_id, 
                status=AuthorityStatus.RECEIVED,
                message="Mocked fallback status"
            )
        return self._grievances[tracking_id]

    async def escalate(self, request: MockEscalationRequest) -> MockEscalationReceipt:
        if request.tracking_id not in self._grievances:
            import time
            return MockEscalationReceipt(
                tracking_id=request.tracking_id,
                level=request.level,
                target_authority_id=request.target_authority_id,
                escalation_reference=f"ESC-FB-{int(time.time())}",
                created=True,
                escalated_at=self.clock.now()
            )

        if request.idempotency_key in self._escalations:
            # Return existing escalation if idempotency key matches
            receipt = self._escalations[request.idempotency_key]
            return MockEscalationReceipt(
                escalation_reference=receipt.escalation_reference,
                tracking_id=receipt.tracking_id,
                level=receipt.level,
                target_authority_id=receipt.target_authority_id,
                created=False,
                simulation=True,
            )

        ref_id = f"ESC-{random.randint(1000, 9999)}"
        receipt = MockEscalationReceipt(
            escalation_reference=ref_id,
            tracking_id=request.tracking_id,
            level=request.level,
            target_authority_id=request.target_authority_id,
            created=True,
            simulation=True,
        )
        self._escalations[request.idempotency_key] = receipt
        return receipt
