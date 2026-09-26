# SPANDAN AI — Listen. Respond. Resolve.

Build for Billions · Agentic AI for Billions track · Autonomous Civic Grievance Redressal Agent

> **Hackathon prototype — Phase 1–4 checkpoint.** All civic data is *DEMO CIVIC RULE /
> prototype configuration*, not official policy. Nothing is filed with any government
> system. SPANDAN AI never resolves problems itself; resolution stays with human authorities.

## 1. What SPANDAN AI does (today)

A citizen reports a civic problem once, by voice or text, in English, Tamil, Telugu, Hindi,
Kannada or Malayalam. SPANDAN AI:

1. **Understands** it (Phase 2): extracts issue, location and duration from the citizen's own
   words and shows "What I understood". Nothing advances until the citizen **confirms**.
2. **Classifies** it (Phase 3): civic category, responsible department and ward, from a
   **local civic knowledge base** (ChromaDB, embedded) with provenance for every decision. It
   asks a question instead of guessing when information is missing or ambiguous.
3. **Drafts** it (Phase 4): a grounded administrative complaint draft that adds no facts. The
   citizen reviews, edits (every edit is a new version) and approves it.

The end state of this checkpoint is **"Draft approved and ready for filing."** Filing itself is
a later phase and has not happened.

## 2. Implemented vs. future phases

| Phase | Scope | State |
| --- | --- | --- |
| 1 | Foundation: layers, contracts, state machine, audit trail, config, UI shell | **Done** |
| 2 | Offline-first multilingual intake, voice, confirmation | **Done** |
| 3 | Local RAG, classification, department + jurisdiction reasoning | **Done** |
| 4 | Fact-locked drafting, validation, versioned citizen review and approval | **Done** |
| 5 | Mock government API filing, tracking ID | **Not implemented** |
| 6–10 | Orchestration, simulated SLA clock, Autonomous Watchdog, escalation, authority view, explanations | **Not implemented** |

There is no filing, tracking ID, SLA, notification, officer assignment or escalation in this
build. The Filing and Watchdog agents exist only as contracts that return 501 naming their
phase. The authority page is a labelled placeholder.

## 3. Flow

```
Citizen → Intake → Confirmation → Classification + RAG → Drafting → Citizen review → Approval → [Future: Filing → Monitoring → Escalation]
```

Details: [`docs/architecture.md`](docs/architecture.md), [`docs/intake.md`](docs/intake.md),
[`docs/classification.md`](docs/classification.md), [`docs/drafting.md`](docs/drafting.md).

## 4. Offline mode and optional AI

Everything works with **no internet and no API key**:

- a deterministic offline intake engine with six language resource files
- a local knowledge base with a deterministic hashing embedder
- deterministic templates for drafting

Gemini (`GEMINI_API_KEY`) is an optional assistant for wording and gap-filling. Its output is
always validated, and a failure falls back to the offline result. Browser speech recognition
needs no key. Server speech-to-text for uploaded audio is optional: a local faster-whisper model
(not bundled) or remote Whisper (`OPENAI_API_KEY`). The optional `onnx-minilm` embedder is not
bundled either; if it cannot be loaded, the app reports the knowledge base as unavailable
(503) instead of crashing.

## 5. Repository layout

```
backend/          FastAPI app (Python 3.11): api, agents, services, repositories, models, schemas
backend/config/   Language list, drafting templates and administrative vocabulary
backend/resources/intake/  Offline language resources (en, ta, te, hi, kn, ml) + safety phrases
knowledge_base/   Civic knowledge base (DEMO CIVIC RULE): categories, departments, wards, guidelines
frontend/         React 19 + Vite + TypeScript + Tailwind
docs/             Architecture, per-phase design, phase reports, consolidation report
scripts/          Secret check, dev seed data, KB ingestion, offline demos
```

## 6. Setup

Prerequisites: Python 3.11+, Node.js 20+ (tested with 22) and npm.

```bash
cp .env.example .env            # blank keys are fine: everything runs offline

cd backend
python3 -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt

cd ../frontend
npm install
```

## 7. Run

```bash
# Backend  -> http://localhost:8000   (API docs: /docs, schema: /openapi.json)
cd backend && uvicorn app.main:app --port 8000

# Frontend -> http://localhost:5173
cd frontend && npm run dev
```

`curl http://localhost:8000/health` returns `"status": "ok"`. On first start the backend creates
the SQLite database and indexes the knowledge base into `backend/data/chroma` (a few seconds).
Optional sample data: `cd backend && python ../scripts/seed_dev.py`.

## 8. Demo flow

1. Open http://localhost:5173 and choose **Report a problem**.
2. Type (or speak) e.g. *"Street light on Main Road has not been working for three days."* or
   the Tamil *"தெரு விளக்கு எரியவில்லை"*.
3. Answer any question SPANDAN AI asks (for example the location), then **confirm** "What I
   understood".
4. **Classify**: you see *Streetlight → Electrical department → Ward 7 (demo)* with the demo
   sources used.
5. **Draft**: review the draft. Edit a section (for example add *"It was repaired previously
   but stopped working again."*). The new version is marked *added by the citizen, not
   verified*, and earlier versions stay in the version history.
6. **Approve**. The page says *"Draft approved and ready for filing. Filing is a later phase
   and has not happened yet."*

The same flow without the UI: `scripts/demo_intake.py`, `scripts/demo_classification.py`,
`scripts/demo_drafting.py` (run with `backend/.venv/bin/python`).

## 9. Environment variables

All variables live in one root `.env` (template: [`.env.example`](.env.example)). No variable
is required.

| Variable | Default | Notes |
| --- | --- | --- |
| `APP_ENV` | `development` | `production` rejects unsafe settings (`FRONTEND_ORIGIN=*`, `LOG_LEVEL=DEBUG`) |
| `LOG_LEVEL` | `INFO` | |
| `DATABASE_URL` | `backend/data/agentx.db` | SQLite (file name kept from Phase 1 for compatibility) |
| `FRONTEND_ORIGIN` | `http://localhost:5173` | CORS allow-list, comma-separated |
| `GEMINI_API_KEY` | — | Optional, server-side only |
| `GEMINI_MODEL` | `gemini-2.5-flash` | |
| `AI_TIMEOUT_SECONDS` | `20` | |
| `SPEECH_TO_TEXT_PROVIDER` | `auto` | `auto`, `local`, `whisper` (requires `OPENAI_API_KEY`), `none` |
| `LOCAL_STT_MODEL_PATH` | — | faster-whisper model directory (not bundled) |
| `OPENAI_API_KEY` | — | Optional remote Whisper |
| `MAX_AUDIO_BYTES` / `MAX_AUDIO_SECONDS` | `10485760` / `120` | Upload limits |
| `KB_VECTOR_DIR` | `backend/data/chroma` | Local ChromaDB directory |
| `KB_EMBEDDING_PROVIDER` | `hashing` | `hashing` (offline) or `onnx-minilm` (optional, not bundled) |
| `KB_AUTO_INGEST` | `true` | Re-index at start-up when missing or stale |
| `MOCK_GOV_API_BASE_URL` / `MOCK_GOV_API_KEY` | — | Reserved for Phase 5; unused |
| `VITE_API_BASE_URL` | `http://localhost:8000` | Frontend. Only `VITE_*` values reach the browser; never put a secret there |

## 10. Data and persistence

- **Database:** SQLite, created on start (`create_all`). The tables are `complaints`,
  `intake_records`, `classification_records`, `complaint_drafts` and `audit_events`
  (append-only), plus Phase 1 `sla_records` / `escalations` (empty until later phases).
- **Older databases:** if the database was created by an older build with missing columns,
  start-up stops with a clear message and **does not modify the file**. Back it up, then delete
  it (or point `DATABASE_URL` elsewhere).
- **Reset:** stop the backend and delete `backend/data/`. The knowledge-base index is rebuilt
  automatically, or with `python scripts/ingest_civic_kb.py`.

## 11. Tests and quality checks

```bash
cd backend && pytest                  # 291 tests (unit, API, persistence, end-to-end, offline)
cd backend && ruff check app tests
cd frontend && npm test               # 43 tests
cd frontend && npm run typecheck && npm run lint && npm run build
python scripts/demo_intake.py         # 10 offline intake demos
python scripts/demo_classification.py # 10 offline classification demos
python scripts/demo_drafting.py       # 8 offline drafting demos
scripts/check_secrets.sh              # before every push
```

## 12. Security and known limitations

- **No authentication or authorization.** Anyone who can reach the API can read and change
  complaints. This is acceptable for a local demo, but **real authentication, per-citizen
  access control and rate limiting are a production requirement before any deployment**.
- Secrets are read only from the environment, held as `SecretStr` and never logged, returned
  or sent to the frontend. Logs do not contain citizen text or prompts.
- **Dependency audit:** `npm audit` reports 0 vulnerabilities. `pip-audit` reports advisories
  in `chromadb 1.5.9` that have no fixed release yet. They concern Chroma's server mode;
  SPANDAN AI uses only the embedded client, never a Chroma server.
- **Language and data:** non-English vocabularies are drafts that need native-speaker
  review. Drafts are written in English and quote the citizen's own words, because no reliable
  offline translation model is available. The default embedder is lexical, not semantic.
- Full list: [`docs/PHASE_1_4_CONSOLIDATION_REPORT.md`](docs/PHASE_1_4_CONSOLIDATION_REPORT.md).

## 13. Team workflow and reports

- Branch rules and module ownership: [`docs/development-workflow.md`](docs/development-workflow.md).
- Phase reports: [`docs/PHASE_1_REPORT.md`](docs/PHASE_1_REPORT.md),
  [`docs/PHASE_2_IMPLEMENTATION_REPORT.md`](docs/PHASE_2_IMPLEMENTATION_REPORT.md),
  [`docs/PHASE_3_IMPLEMENTATION_REPORT.md`](docs/PHASE_3_IMPLEMENTATION_REPORT.md),
  [`docs/PHASE_4_IMPLEMENTATION_REPORT.md`](docs/PHASE_4_IMPLEMENTATION_REPORT.md) and the
  [Phase 1–4 consolidation report](docs/PHASE_1_4_CONSOLIDATION_REPORT.md).
