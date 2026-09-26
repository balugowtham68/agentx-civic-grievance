"""Turns the configured civic knowledge base into retrievable documents.

Sources (all under knowledge_base/, controlled configuration only):
- categories/categories.json   -> one summary chunk + one phrase chunk per language per category
- rules/*.md                   -> one chunk per "## " section (guidelines, with front matter)
- departments, jurisdictions, timelines JSON -> one chunk per record

Every document carries provenance metadata (source id, name, type, version,
official flag, record id). Citizen text is never ingested.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from app.schemas.reference import ID_PATTERN, ReferenceData

SCHEMA_VERSION = "kb-docs-v1"
MAX_CHUNK_CHARS = 1500
_FRONT_MATTER = re.compile(r"^---\n(?P<meta>.*?)\n---\n(?P<body>.*)$", re.DOTALL)
_ID_RE = re.compile(ID_PATTERN)
REQUIRED_METADATA = (
    "source_id", "source_name", "source_type", "source_version", "official", "record_type", "record_id",
)


class KnowledgeBaseError(RuntimeError):
    """The knowledge base is malformed, missing or stale. Classification must not run."""


@dataclass(frozen=True)
class KnowledgeDocument:
    id: str
    text: str
    metadata: dict[str, str | int | float | bool] = field(default_factory=dict)


def _source_meta(data: ReferenceData, source_id: str | None) -> dict[str, str | bool]:
    if not source_id or source_id not in data.sources:
        raise KnowledgeBaseError(f"record without provenance (source {source_id!r})")
    source = data.sources[source_id]
    return {
        "source_id": source.id,
        "source_name": source.name,
        "source_type": source.type,
        "source_version": source.version,
        "official": source.official,
    }


def _parse_front_matter(path: Path) -> tuple[dict[str, str], str]:
    match = _FRONT_MATTER.match(path.read_text(encoding="utf-8"))
    if not match:
        raise KnowledgeBaseError(f"{path.name}: missing front matter")
    meta: dict[str, str] = {}
    for line in match.group("meta").splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            meta[key.strip()] = value.split("#", 1)[0].strip()
    return meta, match.group("body")


def _guideline_documents(data: ReferenceData, kb_dir: Path) -> list[KnowledgeDocument]:
    rules_dir = (kb_dir / "rules").resolve()
    known_ids = (
        {c.id for c in data.categories} | {d.id for d in data.departments}
        | {p.id for p in data.sla_policies} | {j.id for j in data.jurisdictions}
    )
    categories_by_id = {c.id: c.category for c in data.categories}
    docs: list[KnowledgeDocument] = []
    seen: set[str] = set()
    for path in sorted(rules_dir.glob("*.md")):
        if path.resolve().parent != rules_dir:  # no symlink escapes
            raise KnowledgeBaseError(f"{path.name}: outside the knowledge base")
        meta, body = _parse_front_matter(path)
        doc_id = meta.get("doc_id", "")
        if not _ID_RE.match(doc_id):
            raise KnowledgeBaseError(f"{path.name}: invalid doc_id {doc_id!r}")
        if doc_id in seen:
            raise KnowledgeBaseError(f"duplicate doc_id {doc_id}")
        seen.add(doc_id)
        refs = [r.strip() for r in meta.get("config_refs", "").strip("[]").split(",") if r.strip()]
        unknown = [r for r in refs if r not in known_ids]
        if unknown:
            raise KnowledgeBaseError(f"{doc_id}: config_refs point to unknown ids {unknown}")
        if meta.get("demo_data", "").lower() != "true":
            raise KnowledgeBaseError(f"{doc_id}: only demo_data documents are configured in this prototype")
        cats = sorted(categories_by_id[r] for r in refs if r in categories_by_id)
        title = next((line[2:].strip() for line in body.splitlines() if line.startswith("# ")), doc_id)
        sections = re.split(r"\n(?=## )", body.strip())
        for index, section in enumerate(sections):
            text = f"{title}\n{section.strip()}"[:MAX_CHUNK_CHARS]
            docs.append(
                KnowledgeDocument(
                    id=f"{doc_id}::s{index}",
                    text=text,
                    metadata={
                        "source_id": doc_id,
                        "source_name": f"{title} ({path.name})",
                        "source_type": "document",
                        "source_version": "1",
                        "official": False,
                        "record_type": "guideline",
                        "record_id": doc_id,
                        "category": cats[0] if len(cats) == 1 else "",
                        "categories": ",".join(cats),
                        "config_refs": ",".join(refs),
                        "language": "en",
                    },
                )
            )
    missing = {g for c in data.categories for g in c.guideline_doc_ids} - seen
    if missing:
        raise KnowledgeBaseError(f"categories reference missing guideline documents {sorted(missing)}")
    return docs


def build_documents(data: ReferenceData, kb_dir: Path) -> list[KnowledgeDocument]:
    """All retrievable documents. Raises KnowledgeBaseError on malformed or duplicate records."""
    if not data.categories:
        raise KnowledgeBaseError("no civic categories are configured")
    docs: list[KnowledgeDocument] = []
    for cat in data.categories:
        base = {
            **_source_meta(data, cat.source_id),
            "record_type": "category",
            "record_id": cat.id,
            "category": cat.category,
            "department_id": cat.department_id,
            "active": cat.active,
        }
        summary = f"{cat.display_name}. {cat.description}"
        if cat.aliases:
            summary += " Typical reports: " + "; ".join(cat.aliases) + "."
        docs.append(KnowledgeDocument(id=f"{cat.id}::summary", text=summary, metadata={**base, "language": "en"}))
        for language, patterns in sorted(cat.issue_patterns.items()):
            text = f"{cat.name_in(language)}: " + "; ".join(patterns)
            docs.append(KnowledgeDocument(id=f"{cat.id}::terms::{language}", text=text, metadata={**base, "language": language}))
    for dept in data.departments:
        docs.append(
            KnowledgeDocument(
                id=f"{dept.id}::record",
                text=f"{dept.name}: {dept.description} Handles: {', '.join(dept.categories)}.",
                metadata={**_source_meta(data, dept.source_id), "record_type": "department", "record_id": dept.id,
                          "department_id": dept.id, "language": "en"},
            )
        )
    for jur in data.jurisdictions:
        docs.append(
            KnowledgeDocument(
                id=f"{jur.id}::record",
                text=f"{jur.name} ({jur.type}). Localities: {', '.join(jur.localities)}. Landmarks: {', '.join(jur.landmarks)}.",
                metadata={**_source_meta(data, jur.source_id), "record_type": "jurisdiction", "record_id": jur.id,
                          "language": "en"},
            )
        )
    for sla in data.sla_policies:
        if sla.source_id and sla.source_id in data.sources:
            docs.append(
                KnowledgeDocument(
                    id=f"{sla.id}::record",
                    text=f"Service timeline (reference only) for {sla.category}: {sla.duration_hours} hours, "
                    f"handled by {sla.department_id}.",
                    metadata={**_source_meta(data, sla.source_id), "record_type": "timeline", "record_id": sla.id,
                              "category": sla.category, "department_id": sla.department_id, "language": "en"},
                )
            )
    docs += _guideline_documents(data, kb_dir)
    ids = [d.id for d in docs]
    duplicates = sorted({i for i in ids if ids.count(i) > 1})
    if duplicates:
        raise KnowledgeBaseError(f"duplicate document ids {duplicates}")
    for doc in docs:
        missing = [k for k in REQUIRED_METADATA if k not in doc.metadata]
        if missing or not doc.text.strip():
            raise KnowledgeBaseError(f"{doc.id}: malformed document (missing {missing or 'text'})")
    return docs


def fingerprint(documents: list[KnowledgeDocument], embedder_name: str) -> str:
    """Changes whenever any document, its metadata or the embedder changes (stale detection)."""
    digest = hashlib.sha256(f"{SCHEMA_VERSION}|{embedder_name}".encode())
    for doc in sorted(documents, key=lambda d: d.id):
        digest.update(json.dumps([doc.id, doc.text, doc.metadata], sort_keys=True, ensure_ascii=False).encode())
    return digest.hexdigest()[:32]
