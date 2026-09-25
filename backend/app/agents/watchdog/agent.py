"""Agent 5 - Autonomous Watchdog (behaviour: Phases 7-8). Core differentiator.

On every scheduler tick, for each active complaint: poll mock API status, track
the SLA, detect approaching deadline and breach, evaluate configured escalation
policies, escalate to a human authority when a policy matches, and record why.

ACKNOWLEDGED != RESOLVED: only the policy's terminal_states (default RESOLVED,
CLOSED) stop the SLA or block escalation.
"""

from __future__ import annotations

from app.agents.base import AgentContext, BaseAgent
from app.core.errors import NotImplementedYetError
from app.repositories import ReferenceRepository
from app.schemas.agents import WatchdogEvaluationRequest, WatchdogEvaluationResult
from app.schemas.enums import AgentName
from app.services.external import EscalationNotifier, MockGovernmentGrievanceAPI


class WatchdogAgent(BaseAgent[WatchdogEvaluationRequest, WatchdogEvaluationResult]):
    name = AgentName.WATCHDOG
    description = "Monitors filed complaints, tracks SLA and escalates by configured policy"
    phase = 7
    input_model = WatchdogEvaluationRequest
    output_model = WatchdogEvaluationResult

    def __init__(
        self,
        mock_gov: MockGovernmentGrievanceAPI,
        reference: ReferenceRepository,
        notifier: EscalationNotifier | None = None,
    ) -> None:
        self.mock_gov = mock_gov
        self.reference = reference
        self.notifier = notifier

    async def _run(
        self, payload: WatchdogEvaluationRequest, context: AgentContext
    ) -> WatchdogEvaluationResult:
        raise NotImplementedYetError("Autonomous Watchdog is implemented in Phases 7-8")
