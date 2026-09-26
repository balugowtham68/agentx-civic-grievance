"""SPANDAN AI - ingest and validate the local civic knowledge base (Phase 3).

Validates every knowledge record (schema, provenance, cross-references,
duplicates), builds the retrievable documents, REPLACES the local ChromaDB
collection (so no stale record survives), and verifies retrieval.

Usage (from the repository root, backend venv active):
    python scripts/ingest_civic_kb.py            # validate + ingest + verify
    python scripts/ingest_civic_kb.py --check    # validate the stored collection only (exit 1 if not ready)
Options: --kb-dir PATH  --vector-dir PATH  --embedder hashing|onnx-minilm
No network access and no API key are needed.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

# Verification queries: each must retrieve its category first (deterministic).
PROBES = {
    "street light not working": "streetlight",
    "garbage not collected": "garbage",
    "water pipe leaking": "water_leakage",
    "no water supply": "water_supply",
    "drain blocked and overflowing": "drainage",
    "pothole on the road": "road_damage",
    "public toilet is dirty": "sanitation",
    "broken bench in the park": "broken_infrastructure",
}


def main() -> int:
    from app.core.config import get_settings
    from app.repositories import ReferenceDataError, ReferenceRepository
    from app.services.knowledge import CivicKnowledgeBase, KnowledgeBaseError, build_embedder

    settings = get_settings()
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--kb-dir", type=Path, default=settings.knowledge_base_dir)
    parser.add_argument("--vector-dir", type=Path, default=settings.kb_vector_dir)
    parser.add_argument("--embedder", default=settings.kb_embedding_provider)
    parser.add_argument("--check", action="store_true", help="validate the stored collection without ingesting")
    args = parser.parse_args()

    try:
        data = ReferenceRepository(args.kb_dir).data
        kb = CivicKnowledgeBase(data, args.kb_dir, args.vector_dir, build_embedder(args.embedder))
    except (ReferenceDataError, KnowledgeBaseError, ValueError) as exc:
        print(f"INVALID knowledge base: {exc}")
        return 1
    print(f"Knowledge base: {args.kb_dir}")
    print(f"  categories: {len(data.categories)}  departments: {len(data.departments)}  "
          f"jurisdictions: {len(data.jurisdictions)}  ambiguity groups: {len(data.ambiguity_groups)}")
    print(f"  sources: {', '.join(f'{s.id} ({s.type}, official={s.official})' for s in data.sources.values())}")
    print(f"  documents: {len(kb.documents)}  embedder: {kb.embedder.name}  fingerprint: {kb.fingerprint}")

    if not args.check:
        count = kb.ingest()
        print(f"Ingested {count} records into {args.vector_dir} (collection replaced; no stale records kept)")

    status = kb.validate()
    print(f"Collection ready: {status.ready}  records: {status.records}/{status.expected_records}  stale: {status.stale}")
    for problem in status.problems:
        print(f"  PROBLEM: {problem}")
    if not status.ready:
        return 1

    failures = 0
    for query, expected in PROBES.items():
        hits = kb.retrieve([query], top_k=3, where={"record_type": "category"})
        top = hits[0].category if hits else None
        ok = top == expected
        failures += not ok
        print(f"  [{'PASS' if ok else 'FAIL'}] retrieve {query!r} -> {top} (source {hits[0].source_id if hits else '-'})")
    print("Retrieval verification passed" if not failures else f"{failures} retrieval check(s) failed")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
