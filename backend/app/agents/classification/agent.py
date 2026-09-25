"""Agent 2 - Classification & Reasoning (behaviour: Phase 3).

Category, department, jurisdiction, SLA policy and category-specific missing
information, grounded in the configured knowledge base via RAG, with evidence.
"""

from __future__ import annotations

from app.agents.base import AgentContext, BaseAgent
from app.core.errors import NotImplementedYetError
from app.repositories import ReferenceRepository
from app.schemas.agents import ClassificationRequest, ClassificationResponse
from app.schemas.enums import AgentName
from app.services.ai import AIProvider
from app.services.external import KnowledgeRetriever


class ClassificationAgent(BaseAgent[ClassificationRequest, ClassificationResponse]):
    name = AgentName.CLASSIFICATION
    description = "Grounds category, department, jurisdiction and SLA in configured civic knowledge"
    phase = 3
    input_model = ClassificationRequest
    output_model = ClassificationResponse

    def __init__(
        self, ai: AIProvider, retriever: KnowledgeRetriever, reference: ReferenceRepository
    ) -> None:
        self.ai = ai
        self.retriever = retriever
        self.reference = reference

    async def _run(
        self, payload: ClassificationRequest, context: AgentContext
    ) -> ClassificationResponse:
        raise NotImplementedYetError("Classification & Reasoning Agent is implemented in Phase 3")
