"""Builds the civic knowledge base and the Classification Agent from settings."""

from __future__ import annotations

from app.agents.classification import ClassificationAgent
from app.core.config import Settings
from app.repositories import ReferenceRepository
from app.services.ai import build_ai_provider
from app.services.knowledge import CivicKnowledgeBase, build_embedder


def build_knowledge_base(settings: Settings, reference: ReferenceRepository) -> CivicKnowledgeBase:
    """Validates every knowledge record (raises KnowledgeBaseError if malformed).
    Does not touch the vector store; call ensure_ready() for that."""
    return CivicKnowledgeBase(
        reference.data,
        settings.knowledge_base_dir,
        settings.kb_vector_dir,
        build_embedder(settings.kb_embedding_provider),
    )


def build_classification_agent(
    settings: Settings, reference: ReferenceRepository, knowledge: CivicKnowledgeBase
) -> ClassificationAgent:
    return ClassificationAgent(build_ai_provider(settings), knowledge, reference)
