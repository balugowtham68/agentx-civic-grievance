# SPANDAN AI architecture

Consolidated at the Phase 1–4 checkpoint: Phase 1 foundation, Phase 2 intake
([`intake.md`](intake.md)), Phase 3 classification and RAG ([`classification.md`](classification.md)),
Phase 4 drafting ([`drafting.md`](drafting.md)). Phases 5–10 are **not implemented**.
This document explains the layers, the five agents, the contracts
between them, and where each later phase plugs in. The approved *Final Project
Blueprint* (written under the earlier working name) is the product source of truth; this file describes the code.

## 1. System overview

```
Citizen UI / Authority UI (React)
        │  REST (JSON), one typed API client
        ▼
FastAPI  ── api/ (HTTP only)
        ▼
services/ (business orchestration, audit, AI provider, external clients)
        ▼
agents/  (Intake · Classification · Drafting · Filing · Watchdog)
        ▼
repositories/ (persistence)  ──►  SQLite
reference repository         ──►  knowledge_base/*.json
external interfaces          ──►  Gemini (optional), speech (optional), local ChromaDB;
                                  Mock Government API (Phase 5, not implemented)
```

Lifecycle: **UNDERSTAND → CLASSIFY → DRAFT → FILE → MONITOR → DECIDE → ESCALATE → EXPLAIN**.

### Implemented flow (Phases 1–4)

```
Citizen (text / voice, 6 languages)
   │
   ▼
Intake (Phase 2) ── offline engine; optional AI, validated ──► "What I understood"
   │                                                             │ clarify / correct
   ▼                                                             ▼
Confirmation (citizen) ─────────── nothing advances without it ──┘
   │
   ▼
Classification + RAG (Phase 3) ── local ChromaDB knowledge base, configured rules,
   │                              department + jurisdiction, provenance; asks when unsure
   ▼
Drafting (Phase 4) ── fact lock → template → validator → optional AI wording (validated)
   │
   ▼
Citizen review ── edits = new versions; citizen-added information flagged "not verified"
   │
   ▼
Approval (citizen) ── complaint DRAFTED: "Draft approved and ready for filing."
   ┊
   ┊  FUTURE (not implemented)
   ▼
[Phase 5 Filing → tracking ID] → [Phase 7 Watchdog / SLA] → [Phase 8 Escalation] → [Phase 9 Authority view + explanations]
```

Every step writes audit events (`intake.*`, `classification.*`, `drafting.*`,
`complaint.*`). No event claims filing, notification, SLA or escalation.

## 2. Layers and ownership

| Layer | Folder | Owns | Must not |
| --- | --- | --- | --- |
| Frontend | `frontend/src` | Presentation | Call `fetch` outside `services/apiClient.ts`; hold secrets |
| API | `backend/app/api` | HTTP: routing, status codes, request/response models | Query the DB or contain business rules |
| Services | `backend/app/services` | Business orchestration, audit recording, AI provider, external clients | Build HTTP responses |
| Agents | `backend/app/agents` | Agent behaviour behind `BaseAgent` | Write the DB or call SDKs directly — they get services injected |
| Repositories | `backend/app/repositories` | Persistence queries | Enforce business rules |
| Models | `backend/app/models` | ORM tables | — |
| Schemas | `backend/app/schemas` | Pydantic contracts and enums shared by all layers | — |
| Core | `backend/app/core` | Config, logging, errors, clock, sanitiser, state machine | — |

A route calls a service, the service calls repositories/agents, e.g.
`POST /api/v1/complaints → ComplaintService.create → ComplaintRepository + AuditService`.

## 3. The five agents

All agents extend `BaseAgent[InputT, OutputT]` (`app/agents/base.py`). `execute()` checks
the input and output contracts, times and logs the run, passes `AppError`s through and
turns anything unexpected into `AgentExecutionError`. Subclasses implement `_run()` only.

| Agent | Input → Output (`app/schemas/agents.py`) | Injected dependencies | Behaviour in |
| --- | --- | --- | --- |
| `IntakeAgent` | `IntakeRequest` → `IntakeResponse` (= `IntakeResult`) | OfflineIntakeEngine (always), CompositeLanguageDetector, ChainTranscriptionProvider, optional AIProvider / TranslationProvider / AIFactExtractor | **Done (Phase 2, offline-first)** |
| `ClassificationAgent` | `ClassificationRequest` → `ClassificationResult` (`app/schemas/classification.py`) | CivicKnowledgeBase (KnowledgeRetriever: local ChromaDB), ReferenceRepository, optional AIProvider | **Done (Phase 3, offline-first)** |
| `DraftingAgent` | `DraftingRequest` → `DraftingResult` (`app/schemas/drafting.py`) | ReferenceRepository (validation), drafting templates, LanguageRegistry, optional AIProvider | **Done (Phase 4, offline-first)** |
| `FilingAgent` | `FilingRequest` → `FilingResponse` | MockGovernmentGrievanceAPI, ReferenceRepository | Phase 5 |
| `WatchdogAgent` | `WatchdogEvaluationRequest` → `WatchdogEvaluationResult` | MockGovernmentGrievanceAPI, ReferenceRepository, EscalationNotifier | Phases 7–8 |

Until their phase, `_run()` raises `NotImplementedYetError` (HTTP 501) naming the phase.
Nothing pretends to work. Intake (Phase 2), Classification (Phase 3) and Drafting (Phase 4) are implemented; Filing and the Watchdog are not.

Contract rules already enforced:
- Extracted facts carry a `source_span` quote from the citizen (no invented facts).
- `FilingRequest` is rejected unless `citizen_confirmed` is true.
- A mock receipt must carry a `CIV-YYYY-NNNN` tracking ID and `simulation: true`.

## 4. Domain model

**Complaint status** (`ComplaintStatus`, transitions in `app/core/state_machine.py`):

```
CREATED → UNDERSTANDING → UNDERSTOOD → CLASSIFYING → CLASSIFIED → DRAFTING → DRAFTED → FILED → MONITORING → WARNING → BREACHED → ESCALATED → RESOLVED → CLOSED
   ↘ NEEDS_INFO ↗  (citizen confirms)   ↘ NEEDS_INFO / NEEDS_REVIEW → CLASSIFYING (answer / retry)   ↘ FILING_FAILED → FILED
DRAFTED → UNDERSTOOD (citizen correction)     MONITORING / WARNING / BREACHED / ESCALATED → RESOLVED | CLOSED
```

Later phases call `ensure_transition(current, target)` before every status change.
`UNDERSTANDING` (Phase 2) means "facts complete, waiting for the citizen to confirm";
only `POST /intake/{id}/confirm` moves a complaint to `UNDERSTOOD`. `CLASSIFYING` (Phase 3)
is the classification run; there is no edge into `CLASSIFIED` except from `CLASSIFYING`.
`DRAFTING` (Phase 4) means a draft exists and awaits the citizen's review; only the citizen's
approval moves it to `DRAFTED` (editing an approved draft moves it back to `DRAFTING`).

**Authority status** (`AuthorityStatus`: NONE, RECEIVED, ACKNOWLEDGED, IN_PROGRESS,
RESOLVED, CLOSED) is what the mock government side reports. **ACKNOWLEDGED ≠ RESOLVED**:
only an escalation policy's `terminal_states` (default `RESOLVED`, `CLOSED`) stop the SLA
or block escalation.

**Tables** (SQLite): `complaints`, `intake_records` (Phase 2: intake result, clarifications, corrections, confirmation), `classification_records` (Phase 3: status, category, department, jurisdiction, answers, source ids, processing mode, result snapshot), `complaint_drafts` (Phase 4: one row per draft version, with the fact set it was built from), `sla_records` (one per complaint: policy, start, warning,
deadline, stage, stop), `escalations` (unique per complaint + level — the duplicate
escalation guard), `audit_events` (append-only; the repository has no update or delete).
All timestamps are timezone-aware UTC; audit events also carry `sim_time` for the Phase 7
simulated clock.

**Reference data** (departments, jurisdictions, authorities, SLA policies, escalation
policies) is configuration in `knowledge_base/*.json`, validated with cross-references at
startup (`ReferenceRepository`). Agents may only use IDs defined there.

## 5. Cross-cutting foundations

- **Config** (`core/config.py`): environment variables via pydantic-settings; secrets are
  `SecretStr`. No key is required in any environment (offline-first); a key is required
  only by the feature that uses it (`SPEECH_TO_TEXT_PROVIDER=whisper` needs `OPENAI_API_KEY`).
  `APP_ENV=production` rejects unsafe settings (wildcard CORS, DEBUG logging).
- **Database** (`database/session.py`): `create_all` adds new tables; a database from an
  older build with missing columns stops start-up with `SchemaMismatchError` and is never
  modified.
- **Path parameters** (`api/params.py`): complaint ids must be UUIDs (422 otherwise);
  tracking ids must match `CIV-YYYY-NNNN`.
- **Errors** (`core/errors.py`): one response shape
  `{"error": {"code", "message", "details", "request_id"}}`. 422 for validation, 404/409/
  501/502 for known errors, 500 with a generic message for anything else (trace in logs).
- **Logging** (`core/logging.py`): one JSON object per line with `request_id`; keys that
  look secret are redacted; citizen text is not logged.
- **Clock** (`core/clock.py`): all "now" goes through `get_clock()`; Phase 7 swaps in the
  accelerated simulated clock.
- **Sanitiser** (`core/security.py`): strips markup and control characters, keeps Indic
  scripts. Applied in `ComplaintCreateRequest`.
- **AI provider** (`services/ai/provider.py`): `AIProvider.generate_structured(PromptSpec,
  schema)`. The only route to Gemini. Prompts are versioned `PromptSpec`s.
- **External interfaces** (`services/external/interfaces.py`): Protocols for the mock
  government API, transcription, translation, knowledge retrieval and escalation notifier.

## 6. API conventions

- Health at `GET /health`; everything else under `/api/v1`.
- JSON only; snake_case fields; enums as upper-case strings; timestamps ISO 8601 UTC.
- `X-Request-ID` accepted and echoed on every response.
- Lists return `{"items": [...], "total": n}` with `limit`/`offset`.
- OpenAPI at `/openapi.json`, Swagger UI at `/docs`.

Phase 1 endpoints:

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/health` | Service, database and configuration check |
| POST | `/api/v1/complaints` | Record a citizen grievance as received (`CREATED`) + audit event |
| GET | `/api/v1/complaints` | List (filter `status`, `limit`, `offset`) |
| GET | `/api/v1/complaints/{id}` | Complaint detail |
| GET | `/api/v1/complaints/{id}/status` | Status, authority status, SLA, escalations |
| GET | `/api/v1/complaints/{id}/audit` | Audit trail |
| GET | `/api/v1/track/{tracking_id}` | Citizen tracking by mock tracking ID |

Phase 2 intake endpoints (`/api/v1/intake/*`) are listed in [`intake.md`](intake.md#api-apiv1)
(the deprecated `/api/v1/complaints/{id}/intake/*` aliases were removed in the consolidation).
Phase 3: `/api/v1/classification/*` ([`classification.md`](classification.md)). Phase 4:
`/api/v1/drafting/*` ([`drafting.md`](drafting.md)). `/api/v1/track/{tracking_id}` answers 404
until Phase 5 issues tracking IDs.

## 7. Where later phases plug in

| Phase | Adds | Extends |
| --- | --- | --- |
| 2 Intake — **done (offline-first)** | `IntakeAgent`, `OfflineIntakeEngine` + six language resource files, script/heuristic/optional-AI language detection, local→remote STT chain, optional Gemini gap-filling and translation, evidence verification for every layer, free-text corrections, confirmation-only `UNDERSTOOD`, `UNDERSTANDING` status, intake endpoints, `intake_records` table, SPANDAN AI intake UI | `agents/intake`, `services/intake` (+ `offline/`), `services/ai`, `prompts/`, `config/languages.json`, `resources/intake/` |
| 3 RAG + classification — **done (offline-first)** | Civic knowledge base (8 demo categories, provenance), local ChromaDB + hashing embeddings, ingestion/validation script, configured rule validation, jurisdiction resolution, category-specific requirements, ambiguity handling, optional validated AI reasoning, `CLASSIFYING` status, `classification_records` table, classification endpoints and UI | `agents/classification`, `services/knowledge`, `services/classification`, `knowledge_base/` |
| 4 Drafting — **done (offline-first)** | Fact-locked `DraftFactSet`, category templates (`config/drafting.json`), `DraftValidator` (no causes/severity/dates/officials/evidence/filing/resolution), optional validated AI wording, versioned citizen edits and approval, `DRAFTING` status, `complaint_drafts` table, drafting endpoints and UI | `agents/drafting`, `services/drafting`, `config/drafting.json` |
| 5 Filing — *not implemented* | Mock Government API service, its HTTP client, `FilingAgent._run`, SLA record creation | `services/external`, `agents/filing` |
| 6 State + audit — *not implemented* | Orchestrator enforcing `ensure_transition`, audit events per stage | `services/` |
| 7 Watchdog — *not implemented* | Simulated clock, APScheduler job, SLA engine | `core/clock.py`, `agents/watchdog` |
| 8 Escalation — *not implemented* | Rule engine over `EscalationPolicy`, idempotent escalation | `agents/watchdog`, `EscalationRepository` |
| 9 Frontend + explain — *not implemented* | Tracking, authority and demo screens, explanation service | `frontend/src/pages`, `services/` |

## 8. Dependencies

Backend (pinned in `backend/requirements.txt`): `fastapi` 0.141 + `starlette` 1.7 (API;
Starlette pinned explicitly to a release without the 0.46.x advisories), `uvicorn` 0.54 (server), `pydantic` + `pydantic-settings`
(contracts and env config), `SQLAlchemy` (ORM and repository layer over SQLite), `httpx`
(test client; Gemini and Whisper REST calls since Phase 2, so no vendor SDKs; mock
government client in Phase 5), `chromadb` (Phase 3: embedded local vector store for the
civic knowledge base; embeddings are computed locally and passed in, telemetry off, no
server; `chromadb` 1.5.9 has open advisories without a fixed release that concern
Chroma's server mode, which is not used). Dev: `pytest` 9.0.3, `ruff`. `faster-whisper` is an optional extra for local
speech-to-text (not installed or bundled).

Frontend: `react`, `react-dom`, `react-router-dom` (routing). Dev: `vite`,
`@vitejs/plugin-react`, `typescript`, `tailwindcss` + `@tailwindcss/vite`, `vitest`,
`jsdom`, `@testing-library/*`, `oxlint` (from the Vite template).

Deliberately not used: LangChain, CrewAI, AutoGen, message brokers, microservices,
Kubernetes, Docker (optional later; local run needs only Python and Node).

## 9. Implementation decisions to note

- **Frontend: React + Vite**, as specified by the Phase 1 prompt. The blueprint's stack
  line said Next.js; Vite is the simpler client for this single-page prototype.
- **Status names** follow the Phase 1 prompt (`WARNING`, `BREACHED`), plus the blueprint's
  `NEEDS_INFO`, `NEEDS_REVIEW` and `FILING_FAILED`.
- **Reference data is JSON config, not DB tables**, so there is one source of truth that
  both the classifier and the RAG documents cite.
- **No migrations** (`create_all`). New tables are added automatically; a changed table is
  detected at start-up (`SchemaMismatchError`) and the local DB must be deleted or replaced.
- **No authentication** in the prototype. Authentication, per-citizen authorization and rate
  limiting are production requirements before any deployment.
