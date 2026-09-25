# AGENT X — Autonomous Civic Grievance Redressal Agent

Build for Billions · Agent AI for Billions track

A citizen reports a civic problem once, by voice or text, in their own language. Five
cooperating agents then **understand → classify → draft → file → monitor → decide →
escalate → explain**. The Autonomous Watchdog keeps following the complaint after the
citizen leaves, and escalates it to a human authority under configured rules when the
service deadline is missed.

> **Hackathon prototype.** Government integration is a mock API, the civic knowledge base
> is demo data, and SLA time is simulated. AGENT X never resolves problems itself;
> resolution stays with human authorities.

**Status: Phase 1 (foundation) complete.** Agent behaviour arrives in Phases 2–10. See
[`docs/architecture.md`](docs/architecture.md) for what exists and what each phase adds.

## Repository layout

```
backend/          FastAPI app (Python 3.11): api, agents, services, repositories, models, schemas
frontend/         React + Vite + TypeScript + Tailwind
knowledge_base/   Demo civic config (JSON) and documents (Markdown) for RAG
docs/             Architecture and development workflow
scripts/          Secret check, dev seed data
```

## Prerequisites

- Python 3.11+
- Node.js 20+ (tested with 22) and npm

## Local setup

```bash
cp .env.example .env            # edit if needed; blank keys are fine for Phase 1

# Backend
cd backend
python3 -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt

# Frontend (new terminal)
cd frontend
npm install
```

## Run

```bash
# Backend  -> http://localhost:8000   (API docs: /docs, schema: /openapi.json)
cd backend && uvicorn app.main:app --reload --port 8000

# Frontend -> http://localhost:5173
cd frontend && npm run dev
```

Check the backend: `curl http://localhost:8000/health` returns `"status": "ok"` and
`"database": "ok"`.

Optional sample data: `cd backend && python ../scripts/seed_dev.py`.

## Environment variables

All variables live in one root `.env` (template: [`.env.example`](.env.example)).

| Variable | Used by | Default | Notes |
| --- | --- | --- | --- |
| `APP_ENV` | backend | `development` | `production` refuses to start without the API keys |
| `LOG_LEVEL` | backend | `INFO` | |
| `DATABASE_URL` | backend | `backend/data/agentx.db` | SQLite |
| `FRONTEND_ORIGIN` | backend | `http://localhost:5173` | CORS allow-list, comma-separated |
| `GEMINI_API_KEY` | backend | — | Server-side only (Phase 2+) |
| `GEMINI_MODEL` | backend | `gemini-2.5-flash` | |
| `MOCK_GOV_API_BASE_URL` | backend | `http://localhost:8001/mock-gov/v1` | Phase 5 |
| `MOCK_GOV_API_KEY` | backend | — | Phase 5 |
| `VITE_API_BASE_URL` | frontend | `http://localhost:8000` | Only `VITE_*` values reach the browser |

## Database

SQLite, created automatically on backend start (`create_all`, no migrations for the
MVP). To reset locally, stop the backend and delete `backend/data/agentx.db`.

## Tests

```bash
cd backend && pytest              # backend (51 tests)
cd backend && ruff check app tests
cd frontend && npm test           # frontend (11 tests)
cd frontend && npm run typecheck && npm run lint && npm run build
scripts/check_secrets.sh          # before every push
```

## Team and workflow

See [`docs/development-workflow.md`](docs/development-workflow.md) for branch rules,
module ownership and how to change a shared contract.
