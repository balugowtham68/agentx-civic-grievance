# SPANDAN AI — Phase 3 Implementation Report (RAG + Classification + Civic Reasoning)

*SPANDAN AI — Listen. Respond. Resolve.*

Labels: **PASS** (implemented and tested), **PARTIAL** (implemented, tested with stated
limits), **NOT TESTED** (implemented, not exercised with the real dependency), **NOT
IMPLEMENTED** (absent by design or out of scope).

## 1. Executive summary

**PHASE 3 STATUS: PASS WITH LIMITATIONS.**

A complaint the citizen confirmed in Phase 2 is classified offline into a civic category,
responsible department and ward, using a local civic knowledge base (ChromaDB, embedded,
with local embeddings) and configured rules. The result explains itself with the
citizen's words and knowledge-base sources. When information is missing, the complaint is
ambiguous or nothing fits, SPANDAN AI asks the citizen or says it cannot classify. It never
guesses. The optional AI is a validated reasoning assistant that cannot override the
knowledge base. Limitations: embeddings are lexical (hashed n-grams), not neural; the neural
option could not be downloaded or tested here. All civic data is demo configuration.
Non-English vocabularies are drafts. Live Gemini is not tested. Nothing was committed or
pushed, and Phase 4 was not started.

## 2. Repository audit (before changes)

| Area | Found |
| --- | --- |
| Phase 1 | FastAPI layers, `BaseAgent`, state machine, audit service, `ReferenceRepository` over `knowledge_base/*.json` (3 departments, 1 ward, 3 SLA policies, 1 rule document), `ClassificationAgent` stub raising `NotImplementedYetError`, `KnowledgeRetriever` Protocol, `complaints.category/department_id/jurisdiction_id` columns. No ChromaDB dependency. |
| Phase 2 | Offline intake, `IntakeHandoff` (`GET /intake/{id}/handoff`), `intake_records`, statuses up to `UNDERSTOOD`, `ProcessingMode`, `ProviderTraceStep`, `ClarificationQuestion`, Phase 2 multilingual text tools (`normalise_with_map`, `PhraseMatcher`) |
| AI | `AIProvider` protocol, `GeminiProvider` (httpx), `FakeAIProvider` for tests |
| Frontend | Intake page, "What I understood", confirm; no classification view |
| Tests | 136 passing (51 Phase 1, 85 Phase 2) |
| Conflicts | Phase 1 stub contract used a numeric `confidence: float` (brief forbids fake confidence). The state machine allowed `UNDERSTOOD → CLASSIFIED` directly. `NEEDS_INFO` is shared by Phase 2 and Phase 3. The Phase 2 handoff only allowed status `UNDERSTOOD`. |

## 3. Phase 2 integration audit

- Phase 3 consumes the existing `IntakeHandoff`. Its builder moved to one module-level function,
  `build_handoff()` in `services/intake/service.py`, used by both the Phase 2 endpoint and
  Phase 3. It refuses anything not `CONFIRMED` (409 `intake_not_confirmed`). A correction
  after confirmation resets the confirmation, so Phase 3 always gets the latest confirmed facts.
- The allowed statuses for the handoff were widened from `UNDERSTOOD` to the post-confirmation
  statuses (`CLASSIFYING`, `CLASSIFIED`, `NEEDS_INFO`, `NEEDS_REVIEW`). This lets re-runs after
  a Phase 3 answer use the same contract.
- Guard added: while a complaint has a classification record, the Phase 2 answer, correction
  and confirm endpoints return 409. Its `NEEDS_INFO` belongs to Phase 3.
- `ClarificationQuestion.field` was extended with `locality | category`. Phase 3 reuses the
  Phase 2 clarification shape instead of a duplicate system. `ProviderTraceStep.stage` gained
  the Phase 3 stages.
- Phase 2 fixes found through Phase 3 demos:
  - English "street light near Main **Road** …" produced the issue "road not working". Subject
    words inside the location phrase are now ignored.
  - Added "nagar" place nouns (ta, te, hi, kn, ml), so "காந்தி நகரில்" is found as a location.
  - Added more instruction-like safety phrases, such as "ignore your instructions".
- All 85 Phase 2 tests still pass. No Phase 2 behaviour was removed.

## 4. Architecture

```
POST /classification/{id}/run → ClassificationService (state, persistence, audit)
   → build_handoff (Phase 2 contract, confirmation gate)
   → CivicKnowledgeBase.ensure_ready (ChromaDB, stale check)
   → ClassificationAgent (BaseAgent contract)
        CivicRuleSet (compiled configured rules) · CivicKnowledgeBase.retrieve (local RAG)
        optional AIProvider (validated) · ReferenceRepository (KB records)
   → classification_records + complaints row + audit_events (existing SQLite DB)
```

No parallel architecture: the same layers, `BaseAgent`, audit service, state machine,
`AIProvider`, reference repository and Phase 2 text utilities are reused.

## 5. RAG architecture

ChromaDB `PersistentClient` (embedded, on disk, telemetry off) → collection
`spandan_civic_kb` (cosine). Embeddings come from `HashingNgramEmbedder` (local, deterministic,
1024-d) and are passed to Chroma explicitly, so no model download and no remote API.
Documents are built by `services/knowledge/documents.py` from the JSON records and Markdown
guidelines, with provenance metadata on every chunk. The ingestion fingerprint (documents +
embedder) is stored as collection metadata for stale detection. **Status: PASS** for local
RAG. **PARTIAL** for "semantic" retrieval: it is lexical and sub-word similarity.

## 6. Knowledge-base schema

`CivicCategory`: `id, category, display_name, display_names, description,
issue_patterns{lang}, aliases, department_id, jurisdiction_type, jurisdiction_required,
required_fields, location_precision, optional_fields, service_guideline,
service_timeline_id, guideline_doc_ids, suppresses, active, source_id`.

The other records are `AmbiguityGroup`, `ClassificationSettings`, `Jurisdiction` (+`aliases`),
`Department`, `SLAPolicy`, and `SourceInfo` (`id, name, type, version, official, label`).
Each file's `source` is attached to every record. A missing provenance, duplicate id,
unknown reference, or prototype source claiming `official: true` is rejected.

## 7. Knowledge-base record count

- 8 civic categories, 6 departments, 2 prototype wards (4 localities, 4 landmarks, aliases
  in 6 scripts), 8 service timelines (reference only), 2 ambiguity groups and 7 guideline
  documents.
- All come from 7 provenance sources, every one `prototype_configuration` and `official: false`.
- **93 retrievable documents** in ChromaDB (56 category chunks, 21 guideline sections,
  6 departments, 2 jurisdictions, 8 timelines).

## 8. Retrieval strategy

Queries are the original text, the issue words, the category answers, the Phase 2 issue
value and the translation if any (the translation only helps retrieval).

- **Categories:** top-k = 8 per query over `record_type=category`, merged by best similarity.
  A candidate needs ≥ 0.20 similarity. A retrieval-only suggestion needs ≥ 0.25, with at
  most 3 suggestions.
- **Guidelines:** filtered by `record_type=guideline` and the chosen category.
- **Tuning:** all thresholds live in `classification_settings.json`, and queries are
  truncated to 2,000 characters.
- **Validation:** `scripts/ingest_civic_kb.py` verifies 8 retrieval probes (8/8 PASS), and
  there are 6 multilingual retrieval tests (PASS).

## 9. Classification logic

1. Configured phrases are matched against the citizen's own words, in tiers: the newest
   category answer first, then the issue words, then the whole statement.
2. Configured suppression is applied (streetlight beats broken infrastructure, garbage beats
   sanitation, drainage beats sanitation).
3. One category left means it is selected: `SUPPORTED` if retrieval also ranked it, otherwise
   `PARTIALLY_SUPPORTED`.
4. Several categories left means `AMBIGUOUS` (the group question if one covers them).
5. No phrase matched: a configured ambiguity term gives `AMBIGUOUS`; retrieval-only
   candidates give `AMBIGUOUS` with suggestions; nothing at all gives
   `UNSUPPORTED_CLASSIFICATION`.
6. Then the optional AI step, department mapping, jurisdiction, required information and
   final evidence validation run.

There is no category logic in code: everything is configuration (`CivicRuleSet`).

## 10. Department mapping — PASS

The department comes only from the category record's `department_id`, validated at load
(the department exists and lists the category) and again at runtime. If the mapping is
missing, the result is `UNSUPPORTED_CLASSIFICATION` (tested by removing a department at
runtime). AI-proposed departments are rejected if unknown, like "Prime Minister's Office",
or if they contradict the mapping.

## 11. Jurisdiction logic — PASS (prototype data)

Configured locality, landmark and alias spellings (6 scripts) are matched in the location
words: newest locality answer first, then the confirmed location (including corrections),
then place entities.

- **Precision:** `EXACT`, `LANDMARK`, `VAGUE` (configured phrases or Phase 2 vague quality)
  or `MISSING`.
- **Status:** `RESOLVED`, `UNRESOLVED`, `AMBIGUOUS` (two wards), `UNSUPPORTED` (a named place
  outside the configured area, after asking) or `NOT_REQUIRED`.
- **Never invented:** ward, address, municipality and coordinates.

## 12. Category-specific required fields — PASS

- **Required for all 8 demo categories:** issue, a specific (non-vague) location, and a
  resolved jurisdiction (`jurisdiction_required: true`).
- **Optional fields per category (brief examples):**
  - streetlight: duration, landmark, pole identifier
  - garbage: duration, frequency, waste type
  - water leakage: duration, severity, visible flow
  - water supply: duration, affected area
- Optional fields are reported as present or "not asked" and **never asked**. Only
  `issue`/`location` may be required, and no personal data fields exist.

## 13. Missing-information handling — PASS

The status is `NEEDS_INFO` with `missing_information` (`location_detail`, `jurisdiction`). One
concise locality question is asked in the complaint's language, e.g. "I understood: garbage
not collected. Please provide the area, street, ward, or nearby landmark." The answer is
stored as citizen evidence and classification re-runs (`NEEDS_INFO → CLASSIFYING → …`).

## 14. Ambiguity handling — PASS

Configured groups exist for water and road. "There is a water problem near my house." gives
`AMBIGUOUS` with "Is the issue a water leak, no water supply, or a drainage problem?". The
answer ("a water leak", "no water supply", or a button with the category name) re-classifies.
The AI is not consulted for configured ambiguity.

## 15. Evidence validation — PASS

- **Citizen evidence:** every category decision carries the exact words that matched,
  sourced as statement, correction or clarification.
- **Final check before `CLASSIFIED`:**
  - the category is active and configured
  - the department is the configured mapping
  - the jurisdiction is configured
  - every knowledge source id exists
  - every citizen quote occurs in the citizen's words
  - Otherwise the result is `UNSUPPORTED_CLASSIFICATION`.
- **AI output** must additionally cite retrieved records, including its category record.

## 16. Explainability — PASS

The explanation is template text built only from the evidence and KB records, for example:
"Your complaint was classified as Streetlight Maintenance because you reported “street
light”. This matches the configured Streetlight Maintenance rule (CAT-STREETLIGHT), and the
local civic knowledge search returned the same category. In this prototype configuration,
Streetlight Maintenance complaints are handled by Electrical Maintenance Department (demo)
(DEPT-ELECTRICAL). “Main Road” matches Main Road in Ward 7 (demo) (WARD-7) … This is DEMO
CIVIC RULE / prototype configuration, not official government policy."

The result also has structured `reasoning` steps with source ids. Explanations are
English-only (PARTIAL for other languages). Questions are localised (drafts).

## 17. Offline mode — PASS

There is no Gemini key, no network access for the demos, no remote embeddings and no
external vector DB. Classification runs from local ChromaDB and configured rules
(`processing_mode: OFFLINE_RULE`). If the KB is missing and auto-ingest is off, classification
returns 503 `knowledge_base_unavailable` and nothing is half-done, while intake keeps working.

## 18. Optional AI mode — PASS with fakes / NOT TESTED live

- **Prompt:** carries the required grounding instruction, untrusted citizen JSON, retrieved
  records, candidates and the resolved jurisdiction.
- **Tested with a scripted provider:**
  - agreement gives `MIXED`
  - contradictions are rejected (a different category, unknown or contradicting department,
    hallucinated ward, uncited record, unverifiable evidence, non-candidate category)
  - malformed JSON or provider failure keeps the offline result
  - AI unavailable gives trace `unavailable`
  - a retrieval-only case is accepted only with verified evidence (`PARTIALLY_SUPPORTED`,
    `MIXED`)
- **Unreachable Gemini** (real `GeminiProvider`, connection error) keeps the offline result
  and the key never leaks.
- **Live Gemini:** NOT TESTED (the host is blocked here).

## 19. Database changes — PASS

New table `classification_records` (existing SQLite DB, created by `create_all`):

- **Queryable columns:** status, confidence state, category, department, jurisdiction,
  processing mode, missing info, source ids, answers, KB version, runs, timestamps.
- **`result`:** a full JSON snapshot.
- **Complaints row:** `category`, `department_id` and `jurisdiction_id` are set only when
  classified.
- **Existing data:** preserved; the database file name is unchanged.
- **Tested:** persistence across restart.

## 20. API endpoints — PASS

`POST /api/v1/classification/{id}/run`, `GET /{id}`, `POST /{id}/retry`, `POST /{id}/answer`,
`GET /{id}/evidence`, `GET /{id}/explanation`, `GET /classification/knowledge-base`.

Complaint ids are validated as UUIDs (422) and answers reuse Phase 2's sanitised
`ClarificationAnswerRequest`. Phase 2 endpoints are not duplicated. `/health` now reports
knowledge-base readiness.

## 21. Frontend changes — PASS

After "Continue" (confirm), the intake page runs classification and shows **How SPANDAN AI
classified it**:

- category, responsible department and jurisdiction (with the citizen's matched words)
- **Why:** the citizen's words and the configured rules
- the explanation
- **Sources:** KB ids
- a DEMO CIVIC RULE / not-official notice
- the processing mode

Other states:

- **What we still need:** question, answer box, and the proposed category marked "not final".
- **We need clarification:** question, option buttons and free answer.
- **We could not classify this:** with retry.
- **Safe error:** with retry (e.g. KB unavailable).

It never shows confidence percentages, similarity scores, prompts or embeddings (tested).
New statuses `CLASSIFYING` ("Being classified") and `NEEDS_REVIEW` ("Could not be
classified").

## 22. Audit events — PASS

| Brief name | Event type |
| --- | --- |
| CLASSIFICATION_STARTED | `classification.started` (run, KB fingerprint, records, embedder) |
| KNOWLEDGE_RETRIEVED | `knowledge.retrieved` (source ids, doc ids, provider) |
| CLASSIFICATION_CANDIDATES_GENERATED | `classification.candidates` |
| CLASSIFICATION_RULE_MATCHED | `classification.rule_matched` (matches as evidence) |
| CLASSIFICATION_NEEDS_INFO | `classification.needs_info` |
| CLASSIFICATION_AMBIGUOUS | `classification.ambiguous` |
| CLASSIFICATION_COMPLETED | `classification.completed` + `complaint.classified` |
| CLASSIFICATION_REJECTED | `classification.rejected` (unsupported, or AI output rejected) + `complaint.needs_review` |
| (citizen answer) | `classification.answered` |

Each event carries `complaint_id`, a timestamp, the event type, `processing_mode` and
`source_ids` where applicable. Some values are shorter than the brief's names because the
existing column holds 32 characters.

## 23. Security — PASS

- **Citizen text is data:** the injection demo is classified from its facts only, with no
  PMO department and a safety flag set.
- **The KB cannot be modified through the API:** there are no write endpoints, and the
  document count is unchanged after an injection attempt.
- **KB changes:** only via configuration plus ingestion.
- **Validation:**
  - path containment for guideline documents
  - ID patterns
  - metadata required keys
  - query length cap
  - request size limit (Phase 1)
- **Secrets:** no secrets in responses, audit or logs (sentinel-key test). The secret scan
  passes.
- **Nothing exposed:** no prompts, hidden instructions or embeddings in responses.

## 24. Test results

| Suite | Result |
| --- | --- |
| Backend pytest | **208 passed** (51 Phase 1 + 85 Phase 2 + 72 Phase 3: 20 knowledge base/RAG, 52 classification) |
| Backend ruff (`app tests ../scripts`) | passed |
| Frontend vitest | **34 passed** (11 Phase 1 + 17 intake + 6 classification) |
| Frontend typecheck (includes tests) / oxlint / vite build | passed / 0 warnings / built |

Coverage by brief category:

- **RAG:** ingestion, persistence, retrieval, metadata, provenance, malformed, duplicate,
  empty, stale.
- **Classification:** all 8 categories.
- **Department:** valid, unsupported, hallucinated.
- **Jurisdiction:** valid, vague, missing, unsupported, ambiguous, required.
- **Missing information:** question, answer, rerun.
- **Ambiguity:** ask, answer, reclassify.
- **Evidence:** supported accepted; unsupported category, department and jurisdiction
  rejected.
- **LLM:** available, unavailable, malformed, hallucinated, injection, contradiction.
- **Offline.**
- **Regression:** all Phase 1 and 2 tests pass.

Two Phase 1 tests changed with the specification:

- The lifecycle path now includes `CLASSIFYING`, because the brief forbids a direct
  `UNDERSTOOD → CLASSIFIED`.
- The "unimplemented agent reports its phase" test now uses the Filing agent (Phase 5),
  because Classification is now implemented.

## 25. Offline validation — PASS

Clean copy (no venv, node_modules, DB or Chroma) → `pip install -r requirements-dev.txt` →
208 passed, ruff clean. `npm ci` → 34 passed; typecheck, lint and build OK.

The backend started with no keys and auto-ingested 93 records:

- `/health` reports `knowledge_base.ready: true`.
- OpenAPI lists all classification paths.
- Over HTTP: unconfirmed run → 409; streetlight → CLASSIFIED WARD-7; garbage → NEEDS_INFO →
  "Gandhi Nagar" → CLASSIFIED WARD-12; water problem → AMBIGUOUS → "no water supply" →
  NEEDS_INFO (vague home location); Tamil → CLASSIFIED WARD-12. Intake demos 10/10 over HTTP.
- `scripts/demo_classification.py`: **10/10 PASS** (streetlight, garbage/vague, water
  ambiguity, prompt injection, hallucinated department rejected, Tamil, Telugu, missing
  jurisdiction, unknown issue, citizen correction).

## 26. Proposal alignment

The Classification & Reasoning Agent determines category, responsible department,
jurisdiction and missing information, using civic rules, mappings, jurisdictions, guidelines
and service timelines. It does exactly that. Timelines are attached as reference data only.
Nothing else is implemented: no drafting, filing, tracking IDs, SLA, watchdog, escalation or
resolution (tested: no tracking ID, no draft, no SLA record, no escalation events). The
original proposal PDF was never received in this project, so alignment is against the
Phase 3 brief.

## 27. Known limitations

- **Embeddings:** `hashing-ngram-v1` is lexical. Paraphrases with no shared words are only
  weakly similar, which is why retrieval never classifies alone (it asks). The neural
  `onnx-minilm` option is implemented but NOT TESTED: the download returned 403 here, and it
  is English-centric.
- **Demo data:** all civic data is DEMO CIVIC RULE / prototype configuration for a fictional
  municipality. There are only 2 wards and 4 localities. Real use needs official sources.
- **Drafts:** non-English phrases, category names, questions and aliases are drafts and need
  native-speaker review. Explanations are English only.
- **Configured phrases:** single-issue complaints only. Negation ("the street light is fine
  but …") is not modelled, and phrases that mention several categories are asked about
  (safe, not smart).
- **`CLASSIFYING` state:** it exists and is audited, but a run completes within one request.
  If the run fails, the transaction rolls back to `UNDERSTOOD`, so `CLASSIFYING` is not
  observable from outside.
- **`UNSUPPORTED_CLASSIFICATION`:** it maps to `NEEDS_REVIEW`. No human-review workflow
  exists yet (later phase).
- **Live AI:** live Gemini reasoning is NOT TESTED.
- **Migrations:** SQLite `create_all` with no migrations.
- **First run:** ChromaDB adds about 460 MB of Python dependencies, and the first import
  takes a few seconds.

## 28. Phase 4 handoff

- **Read only CLASSIFIED complaints:** `GET /api/v1/classification/{id}`, where
  `classification_status == "CLASSIFIED"`.
- **Fields:** `complaint_id`, `category`, `category_record_id`, `category_name`,
  `responsible_department{department_id, name, source_id}`,
  `jurisdiction{jurisdiction_id, name, matched_words, location_precision}`, `evidence`,
  `retrieved_sources` (provenance), `answers`, `service_guideline`, `service_timeline`
  (reference only), `explanation`, `processing_mode`.
- **Plus:** the confirmed Phase 2 facts from `GET /api/v1/intake/{id}/handoff`, and the
  complaint row's `category`, `department_id` and `jurisdiction_id`.
- **State:** the `CLASSIFIED → DRAFTED` transition already exists.

## 29. Files created

- **Backend code:**
  - `app/agents/classification/matching.py`
  - `app/schemas/classification.py`
  - `app/models/classification.py`
  - `app/repositories/classification_repository.py`
  - `app/services/knowledge/{__init__,documents,embeddings,store}.py`
  - `app/services/classification/{__init__,factory,service}.py`
  - `app/api/routes/classification.py`
  - `app/prompts/classification.py`
- **Backend tests:** `tests/test_knowledge_base.py`, `tests/test_classification_api.py`.
- **Knowledge base:**
  - `knowledge_base/categories/{categories,ambiguity_groups,classification_settings}.json`
  - `knowledge_base/rules/{garbage,water,drainage,roads,sanitation,infrastructure}.md`
- **Scripts:** `scripts/ingest_civic_kb.py`, `scripts/demo_classification.py`.
- **Frontend:** `src/components/classification/ClassificationCard.tsx`,
  `tests/classification.test.tsx`.
- **Docs:** `docs/classification.md`, this report.

## 30. Files modified

- **Backend code:**
  - `app/agents/classification/{agent,__init__}.py` (stub → implementation)
  - `app/schemas/{agents,enums,reference,intake,common}.py`
  - `app/core/{state_machine,config}.py`
  - `app/repositories/{reference_repository,__init__}.py`
  - `app/models/__init__.py`
  - `app/services/external/interfaces.py`
  - `app/services/intake/service.py` (`build_handoff`, Phase 3 guard)
  - `app/services/intake/offline/engine.py` (place-phrase fix)
  - `app/api/{deps,router}.py`, `app/api/routes/health.py`, `app/main.py`
  - `requirements.txt` (+`chromadb==1.5.9`)
- **Backend tests:** `tests/{conftest,test_domain}.py`.
- **Backend resources:** `resources/intake/{ta,te,hi,kn,ml,safety}.json`.
- **Knowledge base:**
  - `knowledge_base/README.md`
  - `departments/departments.json`, `jurisdictions/jurisdictions.json`,
    `timelines/sla_policies.json`
  - `escalation/{authorities,escalation_policies}.json` (provenance blocks)
  - `rules/streetlight.md`
- **Frontend:**
  - `src/types/api.ts`, `src/services/spandanApi.ts`, `src/pages/IntakePage.tsx`
  - `src/components/StatusBadge.tsx`, `src/i18n/strings.ts`
  - `tests/intake.test.tsx`
- **Root:** `README.md`, `.env.example`, `docs/architecture.md`.

The Phase 2 changes from the previous session are still uncommitted in the same working tree.

## 31. Commands executed

```bash
pip install chromadb==1.5.9                                  # dependency (PyPI reachable)
python scripts/ingest_civic_kb.py [--vector-dir DIR] [--check]
cd backend && .venv/bin/pytest -o addopts= -q && .venv/bin/ruff check app tests ../scripts
cd frontend && npm test && npm run typecheck && npm run lint && npm run build
python scripts/demo_intake.py [--base-url URL]; python scripts/demo_classification.py
uvicorn app.main:app --port 8766   # clean copy, no keys; /health, /openapi.json, HTTP flows
scripts/check_secrets.sh; git status (no commit)
```

## 32. Final acceptance checklist

| Criterion | Status |
| --- | --- |
| Phase 2 remains functional | PASS (85/85, demos 10/10) |
| Only confirmed complaints enter classification | PASS |
| Local civic knowledge base exists | PASS |
| ChromaDB / local retrieval works | PASS (lexical embeddings; neural NOT TESTED) |
| Knowledge records have provenance | PASS |
| Classification is grounded | PASS |
| Category mapping works | PASS |
| Department mapping works | PASS |
| Jurisdiction logic works | PASS (prototype wards) |
| Category-specific required fields work | PASS |
| Missing information is detected | PASS |
| Ambiguous complaints request clarification | PASS |
| Unsupported classifications are rejected | PASS |
| Hallucinated departments are rejected | PASS |
| Hallucinated jurisdictions are rejected | PASS |
| LLM cannot override civic rules | PASS (scripted provider; live NOT TESTED) |
| Citizen evidence remains authoritative | PASS |
| Multilingual Phase 2 handoff works | PASS (6 languages; draft vocabularies) |
| Offline classification works | PASS |
| External AI is optional | PASS |
| External vector database is not required | PASS |
| Audit trail exists | PASS |
| Explainability exists | PASS (English explanations) |
| Frontend displays classification reasoning | PASS |
| No Phase 4 functionality / filing / tracking / SLA watchdog / escalation | PASS |
| Phase 1 / 2 / 3 tests pass | PASS (208) |
| Backend lint / frontend lint / typecheck / build | PASS |
| Backend starts / OpenAPI works | PASS |
| Secret scan passes | PASS |
| Clean-copy validation passes | PASS |
| SPANDAN AI branding is used | PASS |
| No fictional civic data is presented as official | PASS |
| No fake confidence scores are displayed | PASS |
