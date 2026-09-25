# Development workflow

Five developers share this repository during a 24-hour hackathon. The rules below keep
parallel work from colliding.

## Ownership

| Member | Area | Branch | Main folders |
| --- | --- | --- | --- |
| Balu Gowtham | Architecture, orchestration, integration | `feature/orchestration` | `backend/app/services/` (orchestrator), `backend/app/agents/intake`, `agents/drafting`, `docs/` |
| Guttula Gowtham Gandhi | AI/ML, RAG, classification | `feature/rag-classification` | `backend/app/agents/classification`, `backend/app/services/ai`, `knowledge_base/` |
| Kurella Pardhu | Backend, FastAPI, database, mock API | `feature/backend` | `backend/app/api`, `models`, `repositories`, `database`, `agents/filing`, mock government API |
| Nedam Harshavardhan | Frontend, UX, tracking, audit UI | `feature/frontend` | `frontend/` |
| K. Lakshmi Narasimha Charan | Watchdog, SLA, escalation, testing | `feature/watchdog` | `backend/app/agents/watchdog`, `core/clock.py`, `core/state_machine.py`, `backend/tests/` |

Shared by everyone, changed only with a heads-up: `backend/app/schemas/`,
`frontend/src/types/api.ts`, `.env.example`.

## Branch rules

- `main` is the stable integration branch. Merge into it only when tests pass.
- Work on your feature branch; rebase or merge `main` in often.
- Never force-push a shared branch, delete a teammate's branch, rewrite history, or
  overwrite unrelated work.
- Keep commits focused; avoid drive-by refactoring of other people's modules.

## Before every push

```bash
cd backend && pytest && ruff check app tests
cd frontend && npm test && npm run typecheck && npm run lint
scripts/check_secrets.sh
```

## Changing a shared contract

Schemas in `backend/app/schemas/` and `frontend/src/types/api.ts` are the interfaces
between people. To change one:

1. Prefer adding an optional field over renaming or removing one.
2. Update the backend schema and the frontend type in the same commit.
3. Post the change in the team channel, naming the field and who is affected.
4. Enum values (statuses, event types) are stored in the database — renaming one is a
   breaking change and needs the whole team to delete local databases.

## Adding a dependency

Ask first: is it required, does something we have already do it, will it complicate
integration, is it stable? Then record it in `docs/architecture.md#8-dependencies`.
No agent frameworks (LangChain, CrewAI, AutoGen), brokers or extra services.

## Secrets

- Only `.env.example` is committed; `.env` is git-ignored.
- API keys are read by the backend only. Never put a key in a `VITE_` variable.
