"""Agent 4 - Filing (behaviour: Phase 5).

Confirmed draft -> Mock Government Grievance API -> tracking ID -> persisted
state -> SLA starts. Talks only to the mock API; never a real portal.
"""

from __future__ import annotations

from datetime import timedelta

from app.agents.base import AgentContext, BaseAgent
from app.core.clock import get_clock
from app.repositories import ReferenceRepository
from app.schemas.agents import FilingRequest, FilingResponse
from app.schemas.complaint import SLAStateRead
from app.schemas.enums import AgentName, ComplaintStatus, SLAStage
from app.schemas.mock_gov import MockGrievanceSubmission
from app.services.external.interfaces import MockGovernmentGrievanceAPI


class FilingAgent(BaseAgent[FilingRequest, FilingResponse]):
    name = AgentName.FILING
    description = "Files the confirmed complaint with the mock government API and starts the SLA"
    phase = 5
    input_model = FilingRequest
    output_model = FilingResponse

    def __init__(self, mock_gov: MockGovernmentGrievanceAPI, reference: ReferenceRepository) -> None:
        self.mock_gov = mock_gov
        self.reference = reference
        self.clock = get_clock()

    async def _run(self, payload: FilingRequest, context: AgentContext) -> FilingResponse:
        # 1. Prepare submission
        submission = MockGrievanceSubmission(
            complaint_id=payload.complaint_id,
            complaint=payload.draft
        )

        # 2. Call mock API
        receipt = await self.mock_gov.submit_grievance(submission)

        # 3. Determine SLA
        category = self.reference.category(payload.draft.category)
        sla_policy = self.reference.sla_policy(category.sla_policy_id)

        started_at = receipt.received_at
        warning_at = started_at + timedelta(hours=sla_policy.warning_after_hours)
        deadline_at = started_at + timedelta(hours=sla_policy.duration_hours)

        sla = SLAStateRead(
            policy_id=sla_policy.id,
            started_at=started_at,
            warning_at=warning_at,
            deadline_at=deadline_at,
            stage=SLAStage.ON_TRACK,
        )

        return FilingResponse(
            complaint_id=payload.complaint_id,
            tracking_id=receipt.tracking_id,
            received_at=receipt.received_at,
            simulation=True,
            sla=sla,
            status=ComplaintStatus.MONITORING,
        )
