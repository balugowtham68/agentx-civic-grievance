"""Agent 1 - Citizen Intake (behaviour: Phase 2).

Voice/text in -> transcript, language, translation, extracted issue/location/
duration/entities with source quotes, missing-information detection.
"""

from __future__ import annotations

from app.agents.base import AgentContext, BaseAgent
from app.core.errors import NotImplementedYetError
from app.schemas.agents import IntakeRequest, IntakeResponse
from app.schemas.enums import AgentName
from app.services.ai import AIProvider
from app.services.external import TranscriptionProvider, TranslationProvider


class IntakeAgent(BaseAgent[IntakeRequest, IntakeResponse]):
    name = AgentName.INTAKE
    description = "Understands the citizen's grievance from voice or text in their language"
    phase = 2
    input_model = IntakeRequest
    output_model = IntakeResponse

    def __init__(
        self,
        ai: AIProvider,
        transcription: TranscriptionProvider | None = None,
        translation: TranslationProvider | None = None,
    ) -> None:
        self.ai = ai
        self.transcription = transcription
        self.translation = translation

    async def _run(self, payload: IntakeRequest, context: AgentContext) -> IntakeResponse:
        raise NotImplementedYetError("Citizen Intake Agent is implemented in Phase 2")
