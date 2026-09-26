# SPANDAN AI — Phase 1–4 Consolidation Report

*SPANDAN AI — Listen. Respond. Resolve.* · Build for Billions · Agentic AI for Billions ·
26 Sep 2026

## 1. Summary

Phases 1–4 were audited against the code, which is the source of truth. The consolidation
fixed every defect found that could be fixed without starting Phase 5:

- 2 real Unicode defects
- a knowledge-base failure mode that left an empty index
- an over-strict citizen-edit validator
- an approval/edit inconsistency
- a configuration rule that contradicted offline-first
- dependency advisories in Starlette and pytest
- missing path validation
- deprecated API aliases

The limitations that remain are listed in section 18 with their reasons.

Results:

- Backend: **291 tests pass**, up from 275 at the Phase 4 export.
- Frontend: **43 tests pass**.
- Lint, typecheck and build pass.
- Offline demos: 10/10, 10/10 and 8/8.
- The clean copy and the exported ZIP were installed, tested, started and driven end to end
  over HTTP.

**Phase 5 functionality: NOT IMPLEMENTED.** The build stops at "Draft approved and ready for
filing."

## 2. Scope and rules followed

- Audit, fix and export only. Nothing from Phase 5 or later was built: no filing, tracking
  IDs, SLA, watchdog, escalation or authority actions.
- No Git operations were performed. The history (`d1c5a8a`, `328564b`) is untouched.
- No tests were deleted or weakened to get green results. Three tests were **rewritten**
  because the behaviour they pinned was deliberately changed (sections 8, 11 and 12). Each
  replacement asserts the new behaviour at least as strictly.
- The database file name (`agentx.db`) was kept for compatibility. `AGENT X` is not used as
  the current project name; it appears only in historical reports and one test comment
  that records the rename.

## 3. Audit method

For each phase:

1. Read the code paths end to end: routes → services → agents → repositories.
2. Compare them with the phase report and docs.
3. Probe edge cases with targeted scripts: Unicode, malformed ids, stale or broken
   knowledge base, outdated database, AI failure and citizen edits.
4. Add a regression test for every defect before fixing it.

The dependency, secret, configuration and frontend-wording audits were run across the whole
repository.

## 4. Phase 1 (foundation) — findings

| Finding | Action |
| --- | --- |
| `APP_ENV=production` refused to start without `GEMINI_API_KEY` and `MOCK_GOV_API_KEY`, but Gemini is optional and the mock government API is Phase 5 | Fixed (section 11) |
| Complaint ids in paths were free strings: a malformed id gave 404 and reached the DB | Fixed: UUID-validated path parameters (`app/api/params.py`), 422 `validation_error` |
| `create_all` could not detect a DB created by an older build (missing columns → 500s later) | Fixed (section 12) |
| Error handler: generic 500, no trace leak | Verified with a new test |
| Filing and Watchdog agents | Verified as contracts only (`NotImplementedYetError`, 501) |

## 5. Phase 2 (intake) — findings

| Finding | Action |
| --- | --- |
| `sanitize_text` stripped ZERO WIDTH JOINER / NON-JOINER (Unicode category Cf), corrupting Malayalam chillu letters and Hindi conjuncts | Fixed: ZWJ/ZWNJ kept; bidi overrides and NUL still removed |
| Evidence slices lost the final code points of a chillu (normalised span end mapped to the wrong original index), so the location evidence failed verification and was dropped | Fixed: span ends tracked separately (`_normalise_with_spans`) |
| Deprecated `/api/v1/complaints/{id}/intake*` aliases still served | Removed; canonical `/api/v1/intake/*` only (test asserts 404/405) |
| Confirmation gate | Verified: classification and drafting answer 409 before confirmation |

## 6. Phase 3 (classification + RAG) — findings

| Finding | Action |
| --- | --- |
| An embedder that failed (for example `onnx-minilm` offline) raised inside `ingest()` **after** the collection was deleted. This left an empty collection carrying the new fingerprint | Fixed: vectors computed before touching the store; failures become `KnowledgeBaseError` (503 `knowledge_base_unavailable`) |
| Retrieval embedder errors surfaced as 500 | Fixed: same wrapper |
| Neural embeddings | Not possible offline (model download blocked); hashing baseline kept (section 18) |
| Provenance, stale-index replacement, ambiguity handling | Verified by the existing tests |

## 7. Phase 4 (drafting) — findings

| Finding | Action |
| --- | --- |
| Citizen edits adding genuine information were **rejected** ("It was repaired previously…") | Fixed: accepted, flagged as citizen-added and unverified (section 9) |
| A safe paraphrase by the optional AI that invented facts without using any configured phrase could pass | Fixed: vocabulary coverage check (D-type words) |
| Editing an approved draft left the approval and the filing payload in place | Fixed (section 10) |
| An AI rejection was recorded only as `validation_failed` | Now also `drafting.fallback` |
| "may" as a date word falsely flagged normal English | Removed from the date list |

## 8. Defects and limitations fixed (complete list)

1. ZWJ/ZWNJ stripped by the sanitiser (Unicode corruption).
2. Chillu evidence slices truncated, so a correct location was dropped.
3. A failing embedder left an empty but "current" knowledge-base index.
4. Embedder errors at retrieval gave a 500 instead of a clear 503.
5. Genuine citizen-added information was rejected in edits.
6. Invented facts paraphrased by the AI without configured phrases were not caught.
7. Editing an approved draft did not withdraw the approval or clear the filing payload.
8. No `drafting.approved`, `drafting.approval_withdrawn` or `drafting.fallback` events.
9. `approved_version` was not exposed, and the UI showed no version history.
10. Production config required keys for optional or future features.
11. Outdated SQLite schemas failed late with 500s instead of at start-up.
12. Malformed complaint ids and tracking ids were not validated.
13. Deprecated intake aliases were still served.
14. Starlette 0.46.2 advisories: upgraded to FastAPI 0.141.1 + Starlette 1.7.0.
15. pytest 8.3.5 advisory PYSEC-2026-1845: upgraded to pytest 9.0.3 (dev only).
16. The secret scan did not cover `OPENAI_API_KEY`: added.
17. Frontend wording: the approved state now reads "Draft approved and ready for filing." The
    authority page is labelled "Future phase".

## 9. Validation model (content kinds A–D)

`DraftValidator` sorts draft text into four kinds:

- **A.** The citizen's exact words.
- **B.** Normalised citizen facts: Phase 2 values and number words.
- **C.** Safe administrative wording: the templates, the builder's fixed phrases and a small
  configured `administrative_vocabulary`.
- **D.** Unsupported new content.

**Generated text** (template or AI) with any D content, invented cause, severity, date,
official, evidence, legal claim, filing or resolution claim is rejected. When that happens
the template draft is used and `FALLBACK_USED` is recorded.

**Citizen edits** may add D content. It is accepted and listed in
`citizen_added_information` as *added by the citizen, not verified*, and the version is
saved as `NEEDS_REVIEW`. The locked facts and the Phase 2/3 evidence are never changed.

Only system contradictions stay hard errors (422 `draft_edit_rejected`):

- a tracking ID
- a claim that the complaint was filed
- another department, ward or category

Edits in the citizen's own language are kept verbatim, including ZWJ.

## 10. Draft versioning and approval consistency

- Every edit creates a new version and earlier versions are immutable. Editing requires
  `based_on_version` equal to the latest version (409 otherwise).
- Only the latest version can be approved. Approval moves the complaint `DRAFTING →
  DRAFTED`, fills `complaints.drafted_complaint` (the future filing payload) and records
  `drafting.approved`, `drafting.completed` and `complaint.drafted`.
- Editing after approval: the approved row becomes `SUPERSEDED` and its content is kept.
  The complaint goes back to `DRAFTING`, `drafted_complaint` is cleared, and
  `drafting.approval_withdrawn` is recorded.
- `GET /drafting/{id}` returns `approved_version`, and the UI shows the full version history.
- Verified across an application restart in `test_end_to_end.py`.

## 11. Configuration

All settings live in `backend/app/core/config.py` (pydantic-settings), with one root `.env`
whose template is `.env.example`. Secrets are `SecretStr`, never logged or returned; `/health`
reports only whether each is configured.

The production rule was corrected:

- **Before:** production required `GEMINI_API_KEY` and `MOCK_GOV_API_KEY`.
- **Now:** no key is required in any environment. A key is required only by the feature that
  uses it (`SPEECH_TO_TEXT_PROVIDER=whisper` needs `OPENAI_API_KEY`).
- Production instead rejects unsafe settings: `FRONTEND_ORIGIN=*` and `LOG_LEVEL=DEBUG`.

`test_production_fails_clearly_when_secrets_missing` was replaced by four tests:

- production starts offline without optional or future keys
- two unsafe production settings fail clearly
- a feature-specific key is enforced

Tunable behaviour stays in configuration files: `backend/config/languages.json`,
`backend/config/drafting.json`, `backend/resources/intake/*` and `knowledge_base/*`.

## 12. Database hardening

SQLite with `create_all` is still used, and no destructive migration was added. At start-up,
`verify_schema()` compares every model table and column with the live database. A database
created by an older build raises `SchemaMismatchError`. The message names the problem, says to
back up and delete `backend/data/agentx.db` or point `DATABASE_URL` elsewhere, and the file
is **never modified** (tested with a real outdated file). Other safeguards:

- Uniqueness: `(complaint_id, version)` on drafts; one intake and one classification record
  per complaint.
- `audit_events` is append-only, and the repository has no update or delete.
- Demo data is not deleted automatically.

## 13. Security audit

- **Secrets:** `scripts/check_secrets.sh` passes. A repository-wide grep for Google, OpenAI
  and GitHub tokens and private keys found nothing. There is no `.env` in the tree or export,
  and `.gitignore` covers `.env*` except `.env.example`.
- **Logging:** JSON logs with secret-looking keys redacted. Citizen text, prompts and model
  reasoning are not logged, and audit payloads hold ids, statuses and field names only.
- **Errors:** one error shape; unexpected errors return a generic `internal_error` with no
  trace, path or SQL (tested).
- **Input:**
  - Pydantic validation on every request, with UUID and tracking-ID path patterns.
  - Text sanitisation removes markup, bidi overrides and control characters, and keeps Indic
    joiners.
  - Request and audio size limits (413).
- **Prompt injection:** citizen and knowledge-base text are marked untrusted data in every
  prompt, and AI output is schema-validated and fact-checked before use. Instruction-like
  citizen text is flagged and left out of the draft body.
- **Frontend:** only `VITE_API_BASE_URL` reaches the browser; there is no key in the bundle.
- **Not present:** authentication, authorization and rate limiting. This is a production
  requirement (section 18); a full authentication system was deliberately not built here.

## 14. Dependency audit

| Tool | Result |
| --- | --- |
| `npm audit` (frontend) | **0 vulnerabilities** |
| `pip-audit -r requirements.txt` | 5 advisory entries, all in `chromadb 1.5.9` (PYSEC-2026-311 (listed twice), PYSEC-2026-3813, PYSEC-2026-3814, PYSEC-2026-3815), **no fixed version published** |
| `pip-audit -r requirements-dev.txt` | Same chromadb entries; the pytest advisory is fixed by 9.0.3 |

**Upgrades:**

- `fastapi` 0.115.x → 0.141.1
- `starlette` 0.46.2 → 1.7.0 (pinned explicitly; fixes the Starlette advisories)
- `uvicorn` → 0.54.0
- `pytest` 8.3.5 → 9.0.3

All tests pass after the upgrades.

The chromadb advisories concern Chroma's **server mode** (HTTP server authentication and
authorization). SPANDAN AI uses only the embedded `PersistentClient`: it never starts or
connects to a Chroma server, and telemetry is off. The advisories are documented, not claimed
as fixed. The Starlette TestClient deprecation warning about `httpx` is filtered in
`pytest.ini`; httpx 0.28 is still supported.

## 15. Frontend honesty

- The approved state reads "Draft approved and ready for filing. Filing is a later phase and
  has not happened yet." The status badge for `DRAFTED` reads "Draft approved — ready for
  filing".
- No screen claims that a complaint was filed, notified, tracked, assigned to an officer,
  under SLA or escalated. The complaint list shows "Not filed yet".
- The authority page says "Future phase — not part of this prototype checkpoint".
- The draft card lists citizen-added information as unverified and shows the version history
  (generated / approved / superseded).

## 16. Tests and regression

| Suite | Result |
| --- | --- |
| Backend `pytest` | **291 passed** (app 6, complaints 10, config 10, domain 20, intake API 52, intake units 33, classification 52, knowledge base 21, drafting API 55, drafting units 17, persistence 8, end-to-end 7) |
| Backend `ruff check app tests` | Passed |
| Frontend `vitest` | **43 passed** (5 files) |
| Frontend `tsc -b` / `oxlint` / `vite build` | Passed |
| Offline demos | Intake 10/10, classification 10/10, drafting 8/8 |

New regression tests cover every fix in section 8, including:

- the full citizen journey, v1→v3 with an approval, across a restart
- no advancement without confirmation
- safe 500s
- outdated database
- Unicode (Malayalam chillu, emoji) end to end
- a failing optional embedder
- citizen-added information in English and the citizen's language
- approval withdrawal on edit
- the production configuration rules

## 17. Offline, clean-copy and end-to-end validation

- **Offline:** the environment blocks Hugging Face, Chroma's model S3 and Gemini. All tests
  and demos ran with no API keys and no model downloads.
- **Clean copy / export:** the final ZIP was extracted into an empty directory, and:
  - a fresh venv was installed from `requirements-dev.txt` and `npm ci` was run
  - the backend and frontend tests were run
  - `uvicorn` and `vite` were started
- **HTTP end to end:** against the running backend, `/health` returned ok, and a complaint went
  through intake → confirm → classify → draft → edit → approve, with the DB, audit trail and
  knowledge index created fresh. The Vite dev server served the app.
- No runtime files (database, Chroma index, `.venv`, `node_modules`, caches, `.env`) are in
  the ZIP.

## 18. Retained limitations (with reasons)

1. **No authentication, authorization or rate limiting.** This is a production requirement
   before any deployment; it is out of scope for this checkpoint.
2. **Phase 5–10 features are absent:** filing, tracking IDs, SLA clock, watchdog, escalation,
   authority actions and explanations.
3. **The default embedder is lexical** (hashing n-grams), not semantic. The optional
   `onnx-minilm` needs a model download that is unavailable offline here; the failure is
   handled gracefully.
4. **Drafts are generated in English**, quoting the citizen's own words. No reliable offline
   translation model is available, and a fabricated translation would be unsafe. Citizens
   can edit in their own language.
5. **Non-English intake vocabularies** are drafts that need native-speaker review.
6. **All civic data** (categories, departments, wards, guidelines) is demo prototype
   configuration, not official policy.
7. **chromadb 1.5.9 advisories** have no fixed release. They concern server mode, which is
   not used.
8. **No schema migrations.** A changed table must be recreated; this is detected safely at
   start-up.
9. **Server speech-to-text** needs an optional local model (not bundled) or a remote key.
   Browser speech recognition depends on the browser.
10. **Single-process SQLite** is suitable for the demo, not for concurrent production load.

## 19. Files changed in the consolidation

**Backend app:**

- `app/api/params.py` (new)
- `app/api/routes/{intake,complaints,classification,drafting}.py`
- `app/core/{config,errors,security}.py`
- `app/database/session.py`
- `app/agents/drafting/{validator,builder,agent,config}.py`
- `app/schemas/{drafting,enums}.py`
- `app/services/drafting/service.py`
- `app/services/intake/offline/text.py`
- `app/services/knowledge/store.py`

**Backend config and dependencies:** `config/drafting.json`, `requirements.txt`,
`requirements-dev.txt`, `pytest.ini`.

**Backend tests:**

- `test_end_to_end.py` (new)
- `test_config.py`, `test_complaints_api.py`, `test_intake_api.py`, `test_drafting_api.py`,
  `test_drafting_units.py`, `test_knowledge_base.py`

**Frontend:**

- `src/types/api.ts`
- `src/i18n/strings.ts`
- `src/components/StatusBadge.tsx`
- `src/components/drafting/DraftCard.tsx`
- `src/pages/PlaceholderPages.tsx`
- `tests/drafting.test.tsx`

**Docs and scripts:**

- `README.md` (rewritten)
- `docs/architecture.md`, `docs/intake.md`, `docs/drafting.md`
- `docs/PHASE_1_REPORT.md` (note on the superseded production rule)
- this report
- `.env.example`, `scripts/check_secrets.sh`, `scripts/seed_dev.py`

The Phase 2, 3 and 4 reports are kept unchanged.

## 20. Export and Phase 5 boundary

**Export:** `SPANDAN_AI_PHASE_1_TO_4_FINAL.zip`, with a single root folder `spandan-ai/`. It
contains:

- the complete source: backend, frontend, knowledge base, config, resources, scripts
- all tests
- the docs and all phase reports
- `.env.example`
- the existing `.git` directory, unmodified

Excluded:

- `.venv`, `node_modules`, `dist`
- `__pycache__`, `.pytest_cache`, `.ruff_cache`, `*.tsbuildinfo`
- `backend/data/` (SQLite DB and Chroma index)
- `.env`, logs, IDE and OS files

The consolidation changes are left **uncommitted** for the team to review and commit.

**Phase 5 boundary:** the next phase starts from an approved draft
(`complaints.drafted_complaint`, `approved_version`) and a complaint in `DRAFTED`. The
`FilingAgent` contract, the `FilingRequest` confirmation rule and the `CIV-YYYY-NNNN`
tracking-ID pattern are in place but unimplemented. **Phase 5 functionality: NOT
IMPLEMENTED.**
