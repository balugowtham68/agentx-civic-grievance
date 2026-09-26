"""Phase 3 local civic knowledge base (RAG): documents, local embeddings, ChromaDB store."""

from app.services.knowledge.documents import KnowledgeBaseError, KnowledgeDocument, build_documents
from app.services.knowledge.embeddings import Embedder, HashingNgramEmbedder, build_embedder
from app.services.knowledge.store import COLLECTION, CivicKnowledgeBase

__all__ = [
    "COLLECTION",
    "CivicKnowledgeBase",
    "Embedder",
    "HashingNgramEmbedder",
    "KnowledgeBaseError",
    "KnowledgeDocument",
    "build_documents",
    "build_embedder",
]
