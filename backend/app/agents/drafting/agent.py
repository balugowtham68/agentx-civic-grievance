"""Agent 3 - Complaint Drafting (behaviour: Phase 4).

Turns the citizen's words plus classification into a structured, reviewable
administrative complaint that preserves the citizen's meaning and adds no facts.
"""

from __future__ import annotations

from app.agents.base import AgentContext, BaseAgent
from app.core.errors import NotImplementedYetError
from app.schemas.agents import DraftRequest, DraftResponse
from app.schemas.enums import AgentName
from app.services.ai import AIProvider


class DraftingAgent(BaseAgent[DraftRequest, DraftResponse]):
    name = AgentName.DRAFTING
    description = "Drafts a structured administrative complaint for citizen review"
    phase = 4
    input_model = DraftRequest
    output_model = DraftResponse

    def __init__(self, ai: AIProvider) -> None:
        self.ai = ai

    async def _run(self, payload: DraftRequest, context: AgentContext) -> DraftResponse:
        raise NotImplementedYetError("Complaint Drafting Agent is implemented in Phase 4")
