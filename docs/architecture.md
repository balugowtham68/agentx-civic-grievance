# AGENT X architecture

Phase 1 foundation. This document explains the layers, the five agents, the contracts
between them, and where each later phase plugs in. The approved *AGENT X — Final Project
Blueprint* is the product source of truth; this file describes the code.

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
external interfaces          ──►  Mock Government API, Gemini, speech, ChromaDB (later phases)
```

Lifecycle: **UNDERSTAND → CLASSIFY → DRAFT → FILE → MONITOR → DECIDE → ESCALATE → EXPLAIN**.

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
| `IntakeAgent` | `IntakeRequest` → `IntakeResponse` | AIProvider, TranscriptionProvider, TranslationProvider | Phase 2 |
| `ClassificationAgent` | `ClassificationRequest` → `ClassificationResponse` | AIProvider, KnowledgeRetriever, ReferenceRepository | Phase 3 |
| `DraftingAgent` | `DraftRequest` → `DraftResponse` | AIProvider | Phase 4 |
| `FilingAgent` | `FilingRequest` → `FilingResponse` | MockGovernmentGrievanceAPI, ReferenceRepository | Phase 5 |
| `WatchdogAgent` | `WatchdogEvaluationRequest` → `WatchdogEvaluationResult` | MockGovernmentGrievanceAPI, ReferenceRepository, EscalationNotifier | Phases 7–8 |

Until their phase, `_run()` raises `NotImplementedYetError` (HTTP 501) naming the phase.
Nothing pretends to work.

Contract rules already enforced:
- Extracted facts carry a `source_span` quote from the citizen (no invented facts).
- `FilingRequest` is rejected unless `citizen_confirmed` is true.
- A mock receipt must carry a `CIV-YYYY-NNNN` tracking ID and `simulation: true`.

## 4. Domain model

**Complaint status** (`ComplaintStatus`, transitions in `app/core/state_machine.py`):

```
CREATED → UNDERSTOOD → CLASSIFIED → DRAFTED → FILED → MONITORING → WARNING → BREACHED → ESCALATED → RESOLVED → CLOSED
   ↘ NEEDS_INFO ↗        ↘ NEEDS_REVIEW       ↘ FILING_FAILED → FILED
DRAFTED → UNDERSTOOD (citizen correction)     MONITORING / WARNING / BREACHED / ESCALATED → RESOLVED | CLOSED
```

Later phases call `ensure_transition(current, target)` before every status change.

**Authority status** (`AuthorityStatus`: NONE, RECEIVED, ACKNOWLEDGED, IN_PROGRESS,
RESOLVED, CLOSED) is what the mock government side reports. **ACKNOWLEDGED ≠ RESOLVED**:
only an escalation policy's `terminal_states` (default `RESOLVED`, `CLOSED`) stop the SLA
or block escalation.

**Tables** (SQLite): `complaints`, `sla_records` (one per complaint: policy, start, warning,
deadline, stage, stop), `escalations` (unique per complaint + level — the duplicate
escalation guard), `audit_events` (append-only; the repository has no update or delete).
All timestamps are timezone-aware UTC; audit events also carry `sim_time` for the Phase 7
simulated clock.

**Reference data** (departments, jurisdictions, authorities, SLA policies, escalation
policies) is configuration in `knowledge_base/*.json`, validated with cross-references at
startup (`ReferenceRepository`). Agents may only use IDs defined there.

## 5. Cross-cutting foundations

- **Config** (`core/config.py`): environment variables via pydantic-settings; secrets are
  `SecretStr`; `APP_ENV=production` fails fast without keys.
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

## 7. Where later phases plug in

| Phase | Adds | Extends |
| --- | --- | --- |
| 2 Intake | `IntakeAgent._run`, `GeminiProvider.generate_structured`, speech/translation providers, intake endpoints, citizen intake UI | `agents/intake`, `services/ai`, `services/external` |
| 3 RAG + classification | ChromaDB indexing of `knowledge_base/**/*.md`, `KnowledgeRetriever`, grounding validator | `agents/classification`, `knowledge_base/` |
| 4 Drafting | `DraftingAgent._run`, review/correct/confirm endpoints | `agents/drafting` |
| 5 Filing | Mock Government API service, its HTTP client, `FilingAgent._run`, SLA record creation | `services/external`, `agents/filing` |
| 6 State + audit | Orchestrator enforcing `ensure_transition`, audit events per stage | `services/` |
| 7 Watchdog | Simulated clock, APScheduler job, SLA engine | `core/clock.py`, `agents/watchdog` |
| 8 Escalation | Rule engine over `EscalationPolicy`, idempotent escalation | `agents/watchdog`, `EscalationRepository` |
| 9 Frontend + explain | Tracking, authority and demo screens, explanation service | `frontend/src/pages`, `services/` |

## 8. Dependencies

Backend: `fastapi` (API), `uvicorn` (server), `pydantic` + `pydantic-settings`
(contracts and env config), `SQLAlchemy` (ORM and repository layer over SQLite), `httpx`
(FastAPI test client now; mock-government HTTP client in Phase 5). Dev: `pytest`, `ruff`.

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
- **No migrations** (`create_all`). Acceptable for a 24-hour MVP; delete the local DB after
  schema changes.
