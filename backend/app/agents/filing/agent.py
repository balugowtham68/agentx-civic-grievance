"""Agent 4 - Filing (behaviour: Phase 5).

Confirmed draft -> Mock Government Grievance API -> tracking ID -> persisted
state -> SLA starts. Talks only to the mock API; never a real portal.
"""

from __future__ import annotations

from app.agents.base import AgentContext, BaseAgent
from app.core.errors import NotImplementedYetError
from app.repositories import ReferenceRepository
from app.schemas.agents import FilingRequest, FilingResponse
from app.schemas.enums import AgentName
from app.services.external import MockGovernmentGrievanceAPI


class FilingAgent(BaseAgent[FilingRequest, FilingResponse]):
    name = AgentName.FILING
    description = "Files the confirmed complaint with the mock government API and starts the SLA"
    phase = 5
    input_model = FilingRequest
    output_model = FilingResponse

    def __init__(self, mock_gov: MockGovernmentGrievanceAPI, reference: ReferenceRepository) -> None:
        self.mock_gov = mock_gov
        self.reference = reference

    async def _run(self, payload: FilingRequest, context: AgentContext) -> FilingResponse:
        raise NotImplementedYetError("Filing Agent is implemented in Phase 5")
