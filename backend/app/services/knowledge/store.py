"""Local civic knowledge base on ChromaDB (embedded, on disk; no server, no network).

- `ingest()` validates every document, then REPLACES the collection so no stale
  record can survive, and stores the fingerprint and embedder name as collection
  metadata.
- `status()` / `validate()` check that the collection exists, is current
  (fingerprint), has the expected records, metadata and embeddings.
- `retrieve()` embeds the query locally and runs a top-k similarity search with
  optional metadata filters. Results carry provenance.

Embeddings are computed by our own local embedder and passed to Chroma
explicitly, so Chroma never downloads a model or calls a remote API. Chroma
telemetry is disabled.
"""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Any

from app.core.logging import get_logger
from app.schemas.classification import KnowledgeBaseStatus, RetrievedKnowledge
from app.schemas.reference import ReferenceData
from app.services.knowledge.documents import (
    REQUIRED_METADATA,
    KnowledgeBaseError,
    KnowledgeDocument,
    build_documents,
    fingerprint,
)
from app.services.knowledge.embeddings import Embedder

logger = get_logger(__name__)
COLLECTION = "spandan_civic_kb"
_LOCK = threading.Lock()


def _client(path: Path) -> Any:
    try:
        import chromadb
        from chromadb.config import Settings as ChromaSettings
    except ImportError as exc:  # pragma: no cover - chromadb is a declared dependency
        raise KnowledgeBaseError("ChromaDB is not installed (pip install -r requirements.txt)") from exc
    path.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(
        path=str(path), settings=ChromaSettings(anonymized_telemetry=False, allow_reset=False)
    )


class CivicKnowledgeBase:
    """The local RAG store. One instance per app; thread-safe for the demo's needs."""

    def __init__(self, data: ReferenceData, kb_dir: Path, vector_dir: Path, embedder: Embedder) -> None:
        self.data = data
        self.kb_dir = kb_dir
        self.vector_dir = vector_dir
        self.embedder = embedder
        self.documents: list[KnowledgeDocument] = build_documents(data, kb_dir)
        self.fingerprint = fingerprint(self.documents, embedder.name)
        self._collection: Any | None = None

    # ------------------------------------------------------------------ lifecycle

    def _embed(self, texts: list[str]) -> list[list[float]]:
        """An embedder that cannot run (e.g. an optional model that is not installed or cannot be
        downloaded offline) makes the knowledge base unavailable - it never crashes the app."""
        try:
            return self.embedder.embed(texts)
        except Exception as exc:  # noqa: BLE001 - any provider failure is reported the same way
            raise KnowledgeBaseError(
                f"Embedding provider {self.embedder.name!r} is unavailable ({type(exc).__name__}). "
                "Use KB_EMBEDDING_PROVIDER=hashing (default, offline) or install the model."
            ) from exc

    def _open(self, create: bool = False) -> Any | None:
        client = _client(self.vector_dir)
        if create:
            return client.get_or_create_collection(COLLECTION, embedding_function=None, metadata={"hnsw:space": "cosine"})
        try:
            return client.get_collection(COLLECTION, embedding_function=None)
        except Exception:  # noqa: BLE001 - chroma raises different types per version when missing
            return None

    def ingest(self) -> int:
        """Replace the collection with the current documents. Returns the record count."""
        with _LOCK:
            vectors = self._embed([d.text for d in self.documents])  # before touching the store: fail without damage
            client = _client(self.vector_dir)
            try:
                client.delete_collection(COLLECTION)
            except Exception:  # noqa: BLE001 - nothing to delete
                pass
            collection = client.create_collection(
                COLLECTION,
                embedding_function=None,
                metadata={
                    "hnsw:space": "cosine",
                    "fingerprint": self.fingerprint,
                    "embedder": self.embedder.name,
                    "records": len(self.documents),
                },
            )
            collection.add(
                ids=[d.id for d in self.documents],
                documents=[d.text for d in self.documents],
                metadatas=[d.metadata for d in self.documents],  # type: ignore[misc]
                embeddings=vectors,  # type: ignore[arg-type]
            )
            self._collection = collection
            logger.info("civic knowledge base ingested", extra={"records": len(self.documents), "embedder": self.embedder.name})
            return len(self.documents)

    def status(self) -> KnowledgeBaseStatus:
        collection = self._open()
        if collection is None:
            return KnowledgeBaseStatus(
                ready=False, collection=COLLECTION, records=0, expected_records=len(self.documents),
                embedder=self.embedder.name, fingerprint=None, stale=True, problems=["collection does not exist"],
            )
        meta = collection.metadata or {}
        count = collection.count()
        stale = meta.get("fingerprint") != self.fingerprint
        problems = []
        if stale:
            problems.append("knowledge base changed since the last ingestion (stale)")
        if count != len(self.documents):
            problems.append(f"collection has {count} records, expected {len(self.documents)}")
        return KnowledgeBaseStatus(
            ready=not problems, collection=COLLECTION, records=count, expected_records=len(self.documents),
            embedder=str(meta.get("embedder", "unknown")), fingerprint=meta.get("fingerprint"), stale=stale,
            problems=problems,
        )

    def validate(self) -> KnowledgeBaseStatus:
        """Deep check: every stored record has metadata, an embedding and a known source."""
        status = self.status()
        collection = self._open()
        if collection is None:
            return status
        stored = collection.get(include=["metadatas", "embeddings", "documents"])
        problems = list(status.problems)
        expected = {d.id for d in self.documents}
        ids = list(stored["ids"])
        if set(ids) != expected:
            problems.append(f"stored ids differ from the configured knowledge base ({len(set(ids) ^ expected)} differences)")
        embeddings = stored.get("embeddings")
        for index, doc_id in enumerate(ids):
            meta = (stored.get("metadatas") or [])[index] or {}
            missing = [k for k in REQUIRED_METADATA if k not in meta]
            if missing:
                problems.append(f"{doc_id}: metadata missing {missing}")
            if embeddings is None or len(embeddings[index]) != self.embedder.dimension:
                problems.append(f"{doc_id}: embedding missing or wrong size")
            if meta.get("record_type") == "category" and self.data.category(str(meta.get("category"))) is None:
                problems.append(f"{doc_id}: unknown or inactive category {meta.get('category')!r}")
        return status.model_copy(update={"ready": not problems, "problems": problems})

    def ensure_ready(self, *, auto_ingest: bool) -> KnowledgeBaseStatus:
        status = self.status()
        if not status.ready:
            if not auto_ingest:
                raise KnowledgeBaseError(
                    "Civic knowledge base is not ready (" + "; ".join(status.problems)
                    + "). Run: python scripts/ingest_civic_kb.py"
                )
            logger.info("civic knowledge base missing or stale; ingesting", extra={"problems": status.problems})
            self.ingest()
            status = self.status()
        self._collection = self._open()
        return status

    # ------------------------------------------------------------------ retrieval

    def retrieve(
        self, queries: list[str], *, top_k: int, where: dict[str, Any] | None = None, max_chars: int = 2000
    ) -> list[RetrievedKnowledge]:
        """Top-k per query, merged by best similarity. Queries are truncated to max_chars."""
        queries = [q[:max_chars] for q in queries if q and q.strip()]
        if not queries:
            return []
        collection = self._collection or self._open()
        if collection is None:
            raise KnowledgeBaseError("Civic knowledge base is not available. Run: python scripts/ingest_civic_kb.py")
        result = collection.query(
            query_embeddings=self._embed(queries),  # type: ignore[arg-type]
            n_results=max(1, min(top_k, len(self.documents))),
            where=where,
            include=["documents", "metadatas", "distances"],
        )
        best: dict[str, RetrievedKnowledge] = {}
        for ids, docs, metas, distances in zip(
            result["ids"], result["documents"] or [], result["metadatas"] or [], result["distances"] or []
        ):
            for doc_id, text, meta, distance in zip(ids, docs, metas, distances):
                similarity = round(1.0 - float(distance), 4)
                if doc_id in best and best[doc_id].similarity >= similarity:
                    continue
                best[doc_id] = RetrievedKnowledge(
                    doc_id=doc_id,
                    source_id=str(meta["source_id"]),
                    source_name=str(meta["source_name"]),
                    source_type=str(meta["source_type"]),
                    source_version=str(meta["source_version"]),
                    official=bool(meta["official"]),
                    record_type=str(meta["record_type"]),
                    record_id=str(meta["record_id"]),
                    category=str(meta.get("category") or "") or None,
                    department_id=str(meta.get("department_id") or "") or None,
                    language=str(meta.get("language") or "") or None,
                    content=text or "",
                    similarity=similarity,
                )
        return sorted(best.values(), key=lambda r: r.similarity, reverse=True)[:top_k]
