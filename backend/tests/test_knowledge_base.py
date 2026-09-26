"""Phase 3 - civic knowledge base and local RAG (ChromaDB, local embeddings, provenance)."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from app.repositories import ReferenceDataError, ReferenceRepository
from app.services.knowledge import CivicKnowledgeBase, HashingNgramEmbedder, KnowledgeBaseError

REPO = Path(__file__).resolve().parents[2]
KB = REPO / "knowledge_base"
CATEGORIES = {
    "streetlight", "garbage", "water_leakage", "water_supply", "drainage", "road_damage", "sanitation",
    "broken_infrastructure",
}


def make_kb(kb_dir: Path, vector_dir: Path) -> CivicKnowledgeBase:
    return CivicKnowledgeBase(ReferenceRepository(kb_dir).data, kb_dir, vector_dir, HashingNgramEmbedder())


@pytest.fixture
def kb_copy(tmp_path: Path) -> Path:
    target = tmp_path / "kb"
    shutil.copytree(KB, target)
    return target


def edit_json(path: Path, change) -> None:  # type: ignore[no-untyped-def]
    data = json.loads(path.read_text(encoding="utf-8"))
    change(data)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


# ---------------------------------------------------------------- records and provenance


def test_repository_kb_has_the_eight_demo_categories_with_provenance() -> None:
    data = ReferenceRepository(KB).data
    assert {c.category for c in data.categories} == CATEGORIES
    for record in [*data.categories, *data.departments, *data.jurisdictions, *data.ambiguity_groups]:
        source = data.sources[record.source_id]  # type: ignore[index]
        assert source.type == "prototype_configuration" and source.official is False
        assert source.label == "DEMO CIVIC RULE"
    for category in data.categories:  # every category maps to a configured department
        assert category.category in next(d for d in data.departments if d.id == category.department_id).categories
        assert set(category.issue_patterns) == {"en", "ta", "te", "hi", "kn", "ml"}


def test_prototype_data_cannot_claim_to_be_official(kb_copy: Path) -> None:
    edit_json(kb_copy / "categories" / "categories.json", lambda d: d["source"].update(official=True))
    with pytest.raises(ReferenceDataError, match="cannot be marked official"):
        _ = ReferenceRepository(kb_copy).data


# ---------------------------------------------------------------- ingestion, persistence, validation


def test_ingestion_creates_a_local_collection_with_metadata_and_embeddings(tmp_path: Path) -> None:
    kb = make_kb(KB, tmp_path / "chroma")
    assert kb.status().ready is False  # nothing ingested yet

    count = kb.ingest()
    report = kb.validate()

    assert count == len(kb.documents) == report.records == report.expected_records
    assert report.ready and not report.problems and not report.stale
    assert report.embedder == "hashing-ngram-v1"
    assert {d.metadata["record_type"] for d in kb.documents} == {"category", "guideline", "department", "jurisdiction", "timeline"}


def test_knowledge_base_persists_across_instances(tmp_path: Path) -> None:
    make_kb(KB, tmp_path / "chroma").ingest()
    again = make_kb(KB, tmp_path / "chroma")
    assert again.status().ready  # same fingerprint on disk, no re-ingestion needed
    assert again.ensure_ready(auto_ingest=False).records == len(again.documents)


def test_retrieval_returns_provenance_and_respects_filters(tmp_path: Path) -> None:
    kb = make_kb(KB, tmp_path / "chroma")
    kb.ingest()

    hits = kb.retrieve(["the street light is not working"], top_k=3, where={"record_type": "category"})
    assert hits[0].category == "streetlight" and hits[0].record_id == "CAT-STREETLIGHT"
    assert all(h.record_type == "category" for h in hits)
    top = hits[0]
    assert (top.source_id, top.source_type, top.official) == ("SRC-DEMO-CATEGORIES", "prototype_configuration", False)
    assert top.source_name and top.source_version and top.content
    assert len(kb.retrieve(["water"], top_k=2, where={"record_type": "category"})) == 2  # bounded top-k

    guidelines = kb.retrieve(
        ["streetlight"], top_k=2, where={"$and": [{"record_type": "guideline"}, {"category": "streetlight"}]}
    )
    assert guidelines and all(g.record_id == "KB-RULE-STREETLIGHT-01" for g in guidelines)


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("தெரு விளக்கு எரியவில்லை", "streetlight"),
        ("వీధి దీపం పనిచేయడం లేదు", "streetlight"),
        ("कचरा नहीं उठाया गया", "garbage"),
        ("ರಸ್ತೆಯಲ್ಲಿ ಗುಂಡಿ", "road_damage"),
        ("പൈപ്പ് പൊട്ടി വെള്ളം ചോരുന്നു", "water_leakage"),
        ("There has been no water supply", "water_supply"),
    ],
)
def test_multilingual_retrieval(tmp_path_factory: pytest.TempPathFactory, query: str, expected: str) -> None:
    kb = make_kb(KB, tmp_path_factory.getbasetemp() / "multilingual-chroma")
    kb.ensure_ready(auto_ingest=True)
    assert kb.retrieve([query], top_k=1, where={"record_type": "category"})[0].category == expected


def test_hashing_embedder_is_deterministic_and_normalised() -> None:
    embedder = HashingNgramEmbedder()
    first, second = embedder.embed(["street light not working"]), embedder.embed(["street light not working"])
    assert first == second
    assert abs(sum(v * v for v in first[0]) - 1.0) < 1e-9


# ---------------------------------------------------------------- malformed, duplicate, empty, stale


def test_malformed_category_is_rejected(kb_copy: Path) -> None:
    edit_json(kb_copy / "categories" / "categories.json", lambda d: d["items"][0].update(required_fields=["phone_number"]))
    with pytest.raises(ReferenceDataError, match="required_fields"):
        _ = ReferenceRepository(kb_copy).data


def test_unknown_department_mapping_is_rejected(kb_copy: Path) -> None:
    edit_json(kb_copy / "categories" / "categories.json", lambda d: d["items"][0].update(department_id="DEPT-PRIME-MINISTER"))
    with pytest.raises(ReferenceDataError, match="unknown department DEPT-PRIME-MINISTER"):
        _ = ReferenceRepository(kb_copy).data


def test_duplicate_ids_are_rejected(kb_copy: Path, tmp_path: Path) -> None:
    edit_json(kb_copy / "categories" / "categories.json", lambda d: d["items"].append(dict(d["items"][0])))
    with pytest.raises(ReferenceDataError, match="duplicate category record id"):
        _ = ReferenceRepository(kb_copy).data

    fresh = tmp_path / "kb2"
    shutil.copytree(KB, fresh)
    shutil.copy(fresh / "rules" / "garbage.md", fresh / "rules" / "garbage-copy.md")
    with pytest.raises(KnowledgeBaseError, match="duplicate doc_id"):
        make_kb(fresh, tmp_path / "chroma")


def test_malformed_guideline_document_is_rejected(kb_copy: Path, tmp_path: Path) -> None:
    (kb_copy / "rules" / "broken.md").write_text("# no front matter\nSome text", encoding="utf-8")
    with pytest.raises(KnowledgeBaseError, match="missing front matter"):
        make_kb(kb_copy, tmp_path / "chroma")
    (kb_copy / "rules" / "broken.md").write_text(
        "---\ndoc_id: KB-RULE-X-01\ntype: civic_rule\nconfig_refs: [DEPT-NOWHERE]\ndemo_data: true\n---\n# X\n", encoding="utf-8"
    )
    with pytest.raises(KnowledgeBaseError, match="unknown ids"):
        make_kb(kb_copy, tmp_path / "chroma")


def test_empty_knowledge_base_is_rejected(kb_copy: Path, tmp_path: Path) -> None:
    def empty(data: dict) -> None:  # type: ignore[type-arg]
        data["items"] = []

    edit_json(kb_copy / "categories" / "categories.json", empty)
    edit_json(kb_copy / "categories" / "ambiguity_groups.json", empty)
    with pytest.raises(KnowledgeBaseError, match="no civic categories"):
        make_kb(kb_copy, tmp_path / "chroma")


def test_stale_knowledge_base_is_detected_and_fully_replaced(kb_copy: Path, tmp_path: Path) -> None:
    vectors = tmp_path / "chroma"
    make_kb(kb_copy, vectors).ingest()
    (kb_copy / "rules" / "infrastructure.md").unlink()  # remove a document ...
    edit_json(kb_copy / "categories" / "categories.json", lambda d: d["items"][-1].update(guideline_doc_ids=[]))
    edit_json(kb_copy / "categories" / "categories.json", lambda d: d["items"][0]["aliases"].append("lamp is dead"))

    changed = make_kb(kb_copy, vectors)
    status = changed.status()
    assert status.stale and not status.ready
    with pytest.raises(KnowledgeBaseError, match="python scripts/ingest_civic_kb.py"):
        changed.ensure_ready(auto_ingest=False)

    assert changed.ensure_ready(auto_ingest=True).ready
    stored = {h.record_id for h in changed.retrieve(["broken bench railing footpath"], top_k=20)}
    assert "KB-RULE-INFRASTRUCTURE-01" not in stored  # no stale record survives
    assert changed.validate().ready


def test_missing_collection_without_auto_ingest_fails_clearly(tmp_path: Path) -> None:
    with pytest.raises(KnowledgeBaseError, match="not ready"):
        make_kb(KB, tmp_path / "empty").ensure_ready(auto_ingest=False)


def test_ingest_script_validates_ingests_and_verifies(tmp_path: Path) -> None:
    script = REPO / "scripts" / "ingest_civic_kb.py"
    run = subprocess.run(
        [sys.executable, str(script), "--vector-dir", str(tmp_path / "chroma")],
        capture_output=True, text=True, timeout=120, cwd=REPO,
    )
    assert run.returncode == 0, run.stdout + run.stderr
    assert "Ingested" in run.stdout and "Retrieval verification passed" in run.stdout
    check = subprocess.run(
        [sys.executable, str(script), "--vector-dir", str(tmp_path / "chroma"), "--check"],
        capture_output=True, text=True, timeout=120, cwd=REPO,
    )
    assert check.returncode == 0 and "Collection ready: True" in check.stdout


def test_unavailable_optional_embedding_model_fails_gracefully(settings, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    """KB_EMBEDDING_PROVIDER=onnx-minilm needs a model download; offline that must not crash the app."""
    from fastapi.testclient import TestClient

    from app.main import create_app
    from app.services.knowledge.embeddings import HashingNgramEmbedder

    class BrokenModel(HashingNgramEmbedder):
        name = "broken-model"

        def embed(self, texts: list[str]) -> list[list[float]]:
            raise OSError("model files not found")

    kb = CivicKnowledgeBase(ReferenceRepository(KB).data, KB, tmp_path / "chroma", BrokenModel())
    with pytest.raises(KnowledgeBaseError, match="Embedding provider 'broken-model' is unavailable"):
        kb.ensure_ready(auto_ingest=True)

    with TestClient(create_app(settings.model_copy(update={"kb_vector_dir": tmp_path / "chroma2"}))) as client:
        client.app.state.knowledge = kb  # type: ignore[attr-defined]
        client.app.state.classification_agent.retriever = kb  # type: ignore[attr-defined]
        cid = client.post("/api/v1/intake/text", json={"raw_text": "There is a big pothole on Main Road."}).json()["complaint_id"]
        client.post(f"/api/v1/intake/{cid}/confirm")
        response = client.post(f"/api/v1/classification/{cid}/run")
        assert response.status_code == 503 and response.json()["error"]["code"] == "knowledge_base_unavailable"
        assert "broken-model" in response.json()["error"]["message"]
