# Classification & Reasoning — SPANDAN AI (Agent 2, CLASSIFY)

*SPANDAN AI — Listen. Respond. Resolve.*

Phase 3. Takes a complaint **the citizen has confirmed** in Phase 2 and determines, from the
configured civic knowledge base only: civic category, responsible department, jurisdiction,
category-specific required information, what is missing, whether it is ambiguous, the
evidence, and a plain-language explanation. The successful end state is `CLASSIFIED`.
Nothing here drafts, files, tracks, monitors or escalates (Phases 4+).

> All categories, departments, wards and rules are **DEMO CIVIC RULE / PROTOTYPE
> CONFIGURATION** for a fictional "Sample Municipal Corporation". They are not official
> government policy, and every response says so (`demo_data: true`).

## 1. Pipeline

```
Confirmed Phase 2 handoff (IntakeHandoff; confirmation_status must be CONFIRMED)
  -> citizen evidence: original words, confirmed issue/location (incl. corrections), Phase 3 answers
  -> local retrieval: ChromaDB (embedded) + local hashing n-gram embeddings, top-k, metadata filter
  -> candidates: categories retrieved above the similarity threshold + configured rule matches
  -> deterministic rule validation: configured phrases (6 languages) found in the citizen's words,
     configured suppression ("street light" beats "broken infrastructure"), configured ambiguity groups
  -> optional AI reasoning: may only choose among validated candidates; validated; KB wins on conflict
  -> department mapping from the category record (validated against departments.json)
  -> jurisdiction from the prototype jurisdiction configuration (localities, landmarks, aliases)
  -> category-specific required information
  -> final evidence validation (citizen words + known KB records)
  -> CLASSIFIED | NEEDS_INFO | AMBIGUOUS | UNSUPPORTED_CLASSIFICATION
```

Code: `app/services/knowledge/` (documents, embeddings, ChromaDB store),
`app/agents/classification/` (`matching.py` compiles the configured rules; `agent.py`
decides), `app/services/classification/service.py` (state, persistence, audit),
`app/api/routes/classification.py`, `app/prompts/classification.py`.

## 2. Knowledge base

| File | Contents |
| --- | --- |
| `knowledge_base/categories/categories.json` | 8 category records: patterns per language, aliases, department mapping, required/optional fields, guideline, timeline ref, suppression |
| `knowledge_base/categories/ambiguity_groups.json` | Vague descriptions that fit several categories, with the question to ask (6 languages) |
| `knowledge_base/categories/classification_settings.json` | Retrieval parameters, vague-location phrases, question templates |
| `knowledge_base/departments/departments.json` | 6 demo departments |
| `knowledge_base/jurisdictions/jurisdictions.json` | 2 demo wards with localities, landmarks and aliases in 6 scripts |
| `knowledge_base/timelines/sla_policies.json` | Service timelines — **reference data only**, no SLA runs in Phase 3 |
| `knowledge_base/rules/*.md` | 7 guideline documents (front matter: `doc_id`, `config_refs`, `demo_data`) |

Category record schema (`app/schemas/reference.py::CivicCategory`): `id, category,
display_name, display_names{lang}, description, issue_patterns{lang: [...]}, aliases,
department_id, jurisdiction_type, jurisdiction_required, required_fields, location_precision,
optional_fields, service_guideline, service_timeline_id, guideline_doc_ids, suppresses,
active, source_id`. Every file has a `source` block (`id, name, type, version, official,
label`); its id is attached to every record, and a record without provenance is rejected.
Prototype sources cannot be marked official.

Validation at start-up (and by the ingest command): JSON schema, duplicate ids,
unknown department / SLA / category references, department↔category consistency,
provenance, malformed guideline documents, empty knowledge base. A broken knowledge base
stops the backend with a clear error.

## 3. Local RAG

- **Vector store:** ChromaDB `PersistentClient` in `KB_VECTOR_DIR` (default
  `backend/data/chroma`), collection `spandan_civic_kb`, cosine space, telemetry off. No server.
- **Documents (93):** per category one summary + one phrase chunk per language; one chunk
  per guideline section; one per department, jurisdiction and timeline. Metadata: `source_id,
  source_name, source_type, source_version, official, record_type, record_id, category,
  department_id, language`.
- **Embeddings:** `hashing-ngram-v1` — deterministic hashed word, bigram and character
  3–4-gram features (1024 dims), computed locally and passed to Chroma explicitly, so Chroma
  never downloads a model. It is **lexical/sub-word similarity, not a neural semantic model**.
  Optional `KB_EMBEDDING_PROVIDER=onnx-minilm` uses ChromaDB's local ONNX MiniLM model
  (English-centric; not bundled; **not tested** — its download is blocked in the build environment).
- **Retrieval:** top-k (8) per query over `record_type=category`, merged by best
  similarity; guidelines for the chosen category with a metadata filter. The similarity is a
  retrieval score, never shown as a confidence.
- **Ingestion:** `python scripts/ingest_civic_kb.py` validates, **replaces** the collection
  (no stale records), stores a fingerprint, and verifies retrieval with 8 probes.
  `--check` validates the stored collection only. The backend auto-ingests at start-up when
  the collection is missing or stale (`KB_AUTO_INGEST=true`); with `false` it refuses to
  classify (503 `knowledge_base_unavailable`) until ingested. Citizen text is never ingested.

## 4. Decisions

| Outcome | When | Complaint status |
| --- | --- | --- |
| `CLASSIFIED` | exactly one category's configured phrase is in the citizen's words (after suppression), its department mapping is valid, and required information is present | `CLASSIFIED` |
| `NEEDS_INFO` | category known but location vague or no configured jurisdiction matched (ask for area/street/ward/landmark) | `NEEDS_INFO` |
| `AMBIGUOUS` | several categories' phrases match, a configured ambiguity term matched ("water problem"), or only retrieval found similar categories | `NEEDS_INFO` |
| `UNSUPPORTED_CLASSIFICATION` | nothing matches, the department mapping is invalid, or the citizen's place is outside the configured jurisdictions | `NEEDS_REVIEW` |

`confidence_state` is a controlled value — `SUPPORTED` (rule + retrieval agree),
`PARTIALLY_SUPPORTED` (rule without retrieval agreement, or chosen by the optional AI),
`AMBIGUOUS`, `UNSUPPORTED`. There are no numeric confidence scores.

Retrieval alone never classifies: a complaint with no configured phrase but a similar
category (e.g. "the lamp is dead at night") is `AMBIGUOUS` and the citizen is asked.

Newest citizen input wins: the newest category answer is checked first, then the issue
words, then the whole statement; for location, the newest locality answer first.

## 5. Jurisdiction

`location_precision`: `EXACT` (configured locality, named street/place, or an address with
a number), `LANDMARK` ("near …"), `VAGUE` ("our street", "near my house" — configured
phrases in 6 languages, or Phase 2 `quality: vague`), `MISSING`.
`jurisdiction.status`: `RESOLVED` (configured locality/landmark or alias found in the
citizen's words), `UNRESOLVED`, `AMBIGUOUS` (two wards), `UNSUPPORTED` (the citizen named a
place outside the configured area after being asked), `NOT_REQUIRED`. Addresses, wards,
municipalities and coordinates are never invented.

## 6. Category-specific information

All 8 demo categories require `issue` + `location` (specific, not vague) + a resolved
jurisdiction. Optional fields are listed per category (e.g. streetlight: duration, landmark,
pole identifier; garbage: duration, frequency, waste type; water leakage: duration,
severity, visible flow; water supply: duration, affected area) and are shown as present or
"not asked" — **optional fields are never asked for**, and no personal data is requested.

## 7. Questions and answers

Questions reuse the Phase 2 `ClarificationQuestion` shape (`field: locality | category`),
with templates in the complaint's language (drafts for non-English). The citizen answers
via `POST /classification/{id}/answer`; the answer is stored as citizen evidence
(`citizen_clarification`) and classification re-runs. While a complaint is in Phase 3,
Phase 2 intake endpoints refuse to change it (409).

## 8. Optional AI reasoning

Used only when an AI provider is configured, and never for a configured ambiguity (the
citizen must answer). The prompt says: *"Use only the supplied civic knowledge and citizen
facts. Do not rely on outside knowledge. If the supplied information is insufficient, return
NEEDS_INFO, AMBIGUOUS, or UNSUPPORTED_CLASSIFICATION."* Citizen text is passed as untrusted
JSON. Output is schema-validated, then rejected if: the category is not a validated
candidate; it contradicts a configured rule; the department is unknown or not the configured
mapping; the jurisdiction is not the deterministically resolved one; it cites records that
were not retrieved or not its category record; or its evidence is not in the citizen's
words. Rejections are returned in `rejected_ai_output` and audited
(`classification.rejected`). An accepted AI choice gives `PARTIALLY_SUPPORTED` and
`processing_mode: MIXED`. Explanations are always generated from evidence and KB records,
never from AI prose.

## 9. API (`/api/v1/classification`)

| Method | Path | Result |
| --- | --- | --- |
| POST | `/{id}/run` | Classify a confirmed (`UNDERSTOOD`) complaint; 409 otherwise |
| GET | `/{id}` | Latest `ClassificationResult` |
| POST | `/{id}/retry` | Re-run for `NEEDS_INFO` / `NEEDS_REVIEW` (e.g. after a KB update) |
| POST | `/{id}/answer` | `{text}` — answer the open question; re-runs |
| GET | `/{id}/evidence` | Citizen evidence, rule matches, retrieved records (provenance), source ids |
| GET | `/{id}/explanation` | Plain-language explanation + reasoning steps + source ids |
| GET | `/knowledge-base` | Collection readiness (records, embedder, stale) |

## 10. Audit events

`classification.started`, `knowledge.retrieved`, `classification.candidates`
(CANDIDATES_GENERATED), `classification.rule_matched`, `classification.needs_info`,
`classification.ambiguous`, `classification.completed` + `complaint.classified`,
`classification.rejected` (+ `complaint.needs_review` for unsupported),
`classification.answered`. Payloads carry `processing_mode`, `source_ids` and the decision;
never keys, headers or prompts.

## 11. Phase 4 handoff

A `CLASSIFIED` complaint provides: `complaint_id`, confirmed Phase 2 facts (via the Phase 2
handoff), `category` / `category_record_id`, `responsible_department{department_id, name}`,
`jurisdiction{jurisdiction_id, name, matched_words, location_precision}`, `evidence`,
`retrieved_sources` (provenance), `answers`, `service_guideline`, `service_timeline`
(reference only), `explanation`. The complaint row holds `category`, `department_id`,
`jurisdiction_id`.
