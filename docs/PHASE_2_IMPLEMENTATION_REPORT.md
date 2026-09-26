# SPANDAN AI — Phase 2 Implementation Report (Offline-First Multilingual Citizen Intake)

*SPANDAN AI — Listen. Respond. Resolve.*

Status labels used throughout: **PASS** (implemented and tested), **PARTIAL** (implemented,
tested with limits stated), **NOT TESTED** (implemented, not exercised with the real
dependency), **NOT IMPLEMENTED** (absent by design or out of scope).

## 1. Overall status

**PHASE 2 STATUS: PASS WITH LIMITATIONS.**

Citizen intake works end to end with no internet and no API key, in all six languages,
for text and browser voice; the citizen sees "What I understood" with evidence, answers
questions, corrects (structured or in their own words) and confirms. Limitations: the
non-English vocabularies are drafts needing native-speaker review; there is no local
translation model; local Whisper and the live Gemini / remote Whisper services could not
be tested from this build environment (their hosts are blocked here). Nothing was
committed or pushed. Phase 3 was not started.

## 2. Scope and constraints followed

| Constraint | Result |
| --- | --- |
| No commit / push | PASS — working tree only (`git status` shows changes; HEAD is still the Phase 1 commit `328564b`) |
| Do not start Phase 3 | PASS — no classification, department, category, SLA or escalation logic or UI added |
| Product name SPANDAN AI; do not introduce AGENT X | PASS — UI, API `service` name, docs, HTML title, package name, prompts and error text renamed. The repository folder and the dev DB filename `agentx.db` were left unchanged (renaming would orphan existing local data); both are internal |
| Offline first; no key required | PASS |
| Do not download enormous models without checking hardware | PASS — hardware inspected (section 3); no model downloaded |
| Never persist raw audio | PASS — processed in memory only |
| No secrets in audit/logs/responses | PASS — tested with a sentinel key |
| Do not claim untested capabilities | PASS — see sections 7, 26 |

## 3. Environment and hardware inspection

2 vCPU, 7.8 GB RAM, **no GPU**, 29 GB free disk, Linux. Outbound network is an allow-list:
PyPI and npm reachable; `huggingface.co` (model downloads) and
`generativelanguage.googleapis.com` (Gemini) are **blocked**. Decision: no local LLM or
MT model (CPU-only, 7.8 GB RAM would make even small multilingual models slow, and none
can be downloaded here); local speech-to-text is supported through an optional
faster-whisper provider that the operator installs with a model path. Offline
understanding is therefore rule + lexicon based, which is deterministic and instant.

## 4. Architecture

```
api/routes/intake.py  ->  services/intake/service.py  ->  agents/intake/agent.py (IntakeAgent)
                             (state machine, persistence,      |-- ChainTranscriptionProvider (local -> remote)
                              audit, handoff)                  |-- CompositeLanguageDetector (script -> heuristic -> AI)
                                                               |-- OfflineIntakeEngine (rules + resources/intake/*.json)
                                                               |-- AIFactExtractor (optional, gaps only)
                                                               |-- TranslationProvider (optional)
                                                               `-- verification.py (evidence for every layer)
                          ->  repositories/intake_repository.py -> SQLite table intake_records
```

The agent is built by `services/intake/factory.py` from settings; the offline engine is
always present, optional providers are added only when configured.

## 5. Offline-first design and processing modes — PASS

Offline extraction always runs first. The optional AI runs **only** if `issue` or
`location` is still missing and a key is configured, and it can only fill missing fields.
`processing_mode` ∈ {`OFFLINE_RULE`, `OFFLINE_LOCAL_MODEL`, `OPTIONAL_AI`, `MIXED`} and a
per-stage `provider_trace` are returned, persisted and audited. Tested: no key; key set
but host unreachable (connect error); AI failing; AI filling a gap (`MIXED`); AI not
called when offline found everything; local STT marks `OFFLINE_LOCAL_MODEL`.

## 6. Language detection — PASS (romanised: PARTIAL)

Priority: citizen choice → Unicode script → local romanised heuristics → optional AI →
English only with English evidence, else `und` → `NEEDS_LANGUAGE`. Tested for all five
Indian scripts, Bengali (unsupported → `NEEDS_LANGUAGE`), romanised Tamil and Hindi,
explicit choice overriding the text. Romanised detection uses a small marker list per
language and is PARTIAL.

## 7. Six-language capability matrix

| Language | Offline text (native script) | Romanised | Browser voice | Server voice | Translation | UI strings |
| --- | --- | --- | --- | --- | --- | --- |
| English | PASS (SUPPORTED) | n/a | NOT TESTED in a real browser (mocked Web Speech API tested) | local: NOT TESTED; remote: mocked only | not needed | PASS |
| Tamil | PARTIAL (draft lexicon; demo + extra sentences tested) | PARTIAL | NOT TESTED in real browser | NOT TESTED | FALLBACK (original kept); AI path mocked only | PARTIAL (draft) |
| Telugu | PARTIAL | PARTIAL (markers only) | NOT TESTED | NOT TESTED | FALLBACK | PARTIAL (draft) |
| Hindi | PARTIAL | PARTIAL | NOT TESTED | NOT TESTED | FALLBACK | PARTIAL (draft) |
| Kannada | PARTIAL | PARTIAL (markers only) | NOT TESTED | NOT TESTED | FALLBACK | FALLBACK (English UI, stated) |
| Malayalam | PARTIAL | PARTIAL (markers only) | NOT TESTED | NOT TESTED | FALLBACK | FALLBACK (English UI, stated) |

Returned at runtime by `GET /api/v1/intake/capabilities` (`offline_first: true`).

## 8. Extraction layers — PASS (layer 3 NOT IMPLEMENTED)

1. Rules (English patterns: prepositional locations, durations, identifiers) — PASS.
2. Language dictionaries (`backend/resources/intake/{en,ta,te,hi,kn,ml}.json`): issue
   subject × problem state pairing, place nouns + possessives/postpositions, number word ×
   duration unit, identifier markers; Unicode normalisation with an index map back to the
   original text so evidence is the citizen's exact words — PASS (vocabulary PARTIAL).
3. Optional local model — interface only; **NOT IMPLEMENTED** (no model suitable for this hardware).
4. Optional external AI (Gemini) — implemented; tested with mocked HTTP only (**NOT TESTED live**).

Each fact carries `method` (`rule`, `lexicon`, `ai`, `citizen`) and `quality` (`clear`, `vague`, `partial`).

## 9. Evidence validation (no hallucination) — PASS

`verification.py` validates facts from **every** layer: evidence must occur in the
citizen's statements (case/space/Unicode-normalised) and the value may not introduce
numbers — digits or number words in any of the six languages — that the evidence does
not contain. Rejected facts are returned in `rejected_facts` and audited
(`intake.facts_rejected`). A bare subject inside a place name ("Gandhi **Road**") is not
reported as an issue.

## 10. Romanised input — PARTIAL

Tested: "Enga street light moonu naala eriyala, bus stand pakkathula" → Tamil
(heuristic, `transliterated: true`), issue, location "near bus stand", duration "three
days"; romanised Hindi detection. Coverage is limited to the marker and lexicon words in
the resource files.

## 11. Voice / speech-to-text

| Provider | Status |
| --- | --- |
| Browser Web Speech API | Implemented; UI flow tested with a mocked recogniser. Real-browser accuracy per language: **NOT TESTED** |
| Local (faster-whisper, `LOCAL_STT_MODEL_PATH`) | Implemented; chain and `OFFLINE_LOCAL_MODEL` marking tested with a fake provider. **NOT TESTED with a real model** (cannot download here; package not installed) |
| Remote OpenAI Whisper | Implemented; success and failure tested with mocked HTTP. **NOT TESTED live** |
| Validation | PASS — MIME type (415), magic bytes / damaged WAV (422), size and WAV duration over `MAX_AUDIO_SECONDS` (413); recorder auto-stops at 120 s |
| No server STT available | PASS — 503, text path unaffected, no complaint half-created |
| Audio persistence | PASS — never written to disk or DB |

## 12. Translation — PARTIAL

Provider-based. Offline: `translation.status = UNAVAILABLE`, original kept, extraction
works on the original language (PASS). With AI: English translation added for readers,
never used as evidence (mocked only; NOT TESTED live). Local MT: **NOT IMPLEMENTED**.

## 13. IntakeResult contract — PASS

`complaint_id, input_channel, status, intake_status, original_text, transcript,
language{language, method, transliterated, script, supported}, language_source,
processing_language, translation, translated_text, extracted{issue, location, duration,
entities}, evidence[], rejected_facts[], missing_information[], clarification_questions[],
extraction, processing_mode, provider_trace[], safety_flags[], category_required_fields[]
(empty placeholder for Phase 3), citizen_confirmation_status, clarifications[],
corrections[], created_at, updated_at`. Mirrored in `frontend/src/types/api.ts`.

## 14. Missing information and clarification — PASS

Required: issue, location. Optional: duration. Questions come from resource templates
in the citizen's language and are concise and contextual, e.g. "I understood: street
light not working. Where is this? Please mention a street, area or nearby landmark."
Only required fields are asked about. Vague locations are kept with `quality: vague`
and a UI hint to add a landmark; they do not block confirmation.

## 15. Correction flow — PASS

Structured (`{corrections:[…]}`) or free text (`{text:"No, it is 5 days"}`), parsed
offline by the same engine (no LLM), in the complaint's language (Tamil tested). Leading
yes/no words ignored; unclear text → 422 `correction_not_understood`. Attributed to the
citizen (`source: citizen_correction`, `method: citizen`, evidence = their words). Newest
citizen input wins between corrections and clarification answers. Exactly one form per
request (validated).

## 16. Confirmation and state machine — PASS

New status `UNDERSTANDING` = facts complete, awaiting citizen confirmation. Transitions:
CREATED → UNDERSTANDING | NEEDS_INFO; NEEDS_INFO ↔ UNDERSTANDING; UNDERSTANDING →
UNDERSTOOD **only** via `POST /intake/{id}/confirm` (409 while a required fact is
missing). Tested that intake never reaches CLASSIFIED/DRAFTED/FILED/MONITORING/
ESCALATED/RESOLVED and is locked after confirmation.

## 17. Persistence — PASS

Existing SQLite DB; new table `intake_records` (created automatically). Complaint row
updated with issue/location/duration/language/status. Tested across an app restart.

## 18. Audit events — PASS

`complaint.created`, `intake.received`, `intake.language_detected`,
`complaint.transcribed` (TRANSCRIPTION_COMPLETED), `complaint.translated` /
`intake.translation_failed` (TRANSLATION_COMPLETED), `intake.facts_extracted` (with
processing_mode, provider_trace, safety_flags) / `intake.failed`, `intake.facts_rejected`,
`intake.missing_info_detected`, `complaint.info_requested` (CLARIFICATION_REQUESTED),
`intake.clarification_answered`, `intake.corrected` (CITIZEN_CORRECTION, actor citizen),
`intake.confirmed` + `complaint.understood` (CITIZEN_CONFIRMED). Full sequence asserted in
`test_audit_events_for_a_full_flow`.

## 19. Safety, prompt injection and secrets — PASS

Instruction-like phrases (`resources/intake/safety.json`) are flagged
`instruction_like_text`, audited, shown to the citizen and treated only as complaint
content; state never changes because of text content. AI prompts wrap citizen text as an
untrusted JSON array. A sentinel API key was checked absent from responses, audit trail,
capabilities, health, OpenAPI and logs. `scripts/check_secrets.sh`: passed.

## 20. API — PASS

`GET /intake/capabilities`, `POST /intake/text`, `POST /intake/voice`, `GET /intake/{id}`,
`POST /intake/{id}/process`, `POST /intake/{id}/answer`, `POST /intake/{id}/correction`,
`POST /intake/{id}/confirm`, `GET /intake/{id}/handoff` (all under `/api/v1`), plus
deprecated `/complaints/{id}/intake…` aliases (tested). All in `/openapi.json`.

## 21. Frontend — PASS (real-browser voice NOT TESTED)

SPANDAN AI name and tagline in header, footer and title; language selector (native
names, honest UI-fallback note); text input; voice (browser speech, or recording upload
when the server has STT) with listening/recording states; processing state; "What I
understood" with issue/location/duration, "You said: “…”" evidence and vague hint;
language row (name + how it was found + romanised); offline/online processing indicator
in words; safety notice; clarification questions and answer box; structured Edit and
free-text correction; "Awaiting your confirmation" status; Continue (confirm); safe
error with retry; no department/SLA/escalation UI on intake (tested). API client
switched to canonical `/intake/{id}/…` paths and renamed `spandanApi`.

## 22. Offline demos — PASS (10/10)

`python scripts/demo_intake.py` (in-process, no key, no network) and
`--base-url http://localhost:8765` (running server with no keys) both gave 10/10:

| # | Demo | Result |
| --- | --- | --- |
| 1 | en street light | en (heuristic), UNDERSTANDING, OFFLINE_RULE; issue "street light not working", location "near my house", duration "three days" |
| 2 | ta | ta (script); location "our street" (vague), duration "three days" |
| 3 | te | te (script); same facts |
| 4 | hi | hi (script); location "our lane" |
| 5 | kn | kn (script); same facts |
| 6 | ml | ml (script); same facts |
| 7 | Missing location | NEEDS_INFO; one contextual location question |
| 8 | Correction "No, it is 5 days" + confirm | duration "5 days" (citizen_correction) → UNDERSTOOD |
| 9 | Prompt injection | flagged `instruction_like_text`; still UNDERSTANDING, never RESOLVED |
| 10 | Bengali (unsupported) | NEEDS_LANGUAGE, CREATED, nothing extracted |

## 23. Tests and builds

| Suite | Result |
| --- | --- |
| Backend pytest | **136 passed** (51 Phase 1 + 85 Phase 2: 52 API, 33 unit) |
| Backend ruff (`app tests ../scripts`) | passed |
| Frontend vitest | **28 passed** (11 Phase 1 + 17 intake) |
| Frontend typecheck / oxlint / vite build | passed / 0 warnings / built |

Phase 2 tests by category — LANGUAGE: script detection ×6, romanised detection and
extraction, explicit choice, registry, Bengali. EXTRACTION: six-language demos with exact
evidence spans, entities, Indian-script place names, English rules. SAFETY: prompt
injection (API + unit), no key leakage, malformed/oversized text and audio, number
consistency. OFFLINE: no key, unreachable Gemini, capabilities honesty. FALLBACK:
translation unavailable, AI failure, engine failure (fails safely / falls back to AI),
STT 503/502/504. CORRECTION: structured, free text (en, ta), unclear, newest wins,
one-form rule. CONFIRMATION: incomplete 409, only path to UNDERSTOOD, never beyond,
locked after. REGRESSION: all Phase 1 tests, legacy paths, persistence across restart,
audit sequence.

## 24. Validation performed

Fresh copy (no venv/node_modules/DB) → `pip install -r requirements-dev.txt` → 136 passed,
ruff clean; `npm ci` → 28 passed, typecheck, lint, build OK. Backend started with no
keys: `/health` ok (`service: "SPANDAN AI"`), `/openapi.json` lists all intake paths,
capabilities `offline_first: true`, 10/10 demos over HTTP, romanised Tamil over HTTP,
voice upload with no STT → 503. Secrets scan passed. No commit made.

## 25. Files

**New (backend):** `app/services/intake/offline/{__init__,text,resources,engine}.py`,
`app/services/intake/{__init__,extraction,factory,language_detection,service,speech_to_text,translation}.py`,
`app/agents/intake/{policy,verification}.py`, `app/api/routes/intake.py`,
`app/core/languages.py`, `app/models/intake.py`, `app/prompts/{__init__,intake}.py`,
`app/repositories/intake_repository.py`, `app/schemas/intake.py`,
`config/languages.json`, `resources/intake/{en,ta,te,hi,kn,ml,safety}.json`,
`tests/{fakes,test_intake_api,test_intake_units}.py`.
**New (frontend):** `src/pages/IntakePage.tsx`, `src/components/intake/{LanguagePicker,UnderstoodCard}.tsx`,
`src/hooks/useVoiceInput.ts`, `src/i18n/{languages,strings}.ts`, `src/services/spandanApi.ts`
(replaces `agentxApi.ts`), `tests/intake.test.tsx`.
**New (other):** `scripts/demo_intake.py`, `docs/intake.md`, this report.
**Modified:** backend `agents/{__init__,base}.py`, `agents/intake/agent.py`,
`api/{deps,router}.py`, `core/{config,errors,state_machine}.py`, `main.py`,
`models/__init__.py`, `repositories/__init__.py`, `schemas/{agents,enums,mock_gov}.py`,
`services/ai/{__init__,provider}.py`, `services/complaint_service.py`,
`services/external/{__init__,interfaces}.py`, `tests/{test_app,test_domain}.py`;
frontend `index.html`, `package.json`, `package-lock.json` (name only),
`components/{Layout,StatusBadge}.tsx`, `pages/{ComplaintDetail,Complaints,Home}Page.tsx`,
`services/apiClient.ts`, `types/api.ts`, `tests/{apiClient,app}.test.ts(x)`;
root `.env.example`, `README.md`, `docs/architecture.md`.
**Deleted:** `frontend/src/services/agentxApi.ts`, the earlier draft `docs/PHASE_2_REPORT.md`.
`test_app.py` now expects `service: "SPANDAN AI"` (rename required by the brief).

## 26. Limitations, NOT TESTED and NOT IMPLEMENTED

- Non-English lexicons, questions and UI strings are **drafts**; native-speaker review
  needed before real users. Sentences outside the vocabulary yield fewer facts (and a
  question), never invented ones.
- Only single-complaint statements are modelled; complex multi-issue narratives,
  negation subtleties and code-mixed text beyond the lexicon are PARTIAL at best.
- Generic locations ("our street", "near my house") are accepted as `vague`; precise
  geolocation is not attempted.
- Local speech-to-text with a real model: NOT TESTED. Live Gemini and live Whisper:
  NOT TESTED (mocked HTTP only; hosts blocked here). Real-browser speech accuracy per
  language: NOT TESTED.
- Local translation and local LLM extraction: NOT IMPLEMENTED.
- WAV is the only format whose duration is checked server-side; other formats rely on the
  size limit and the 120 s recorder cap.
- No authentication (prototype); SQLite with `create_all`, no migrations.
- The original proposal PDF was never received in this project, so alignment is
  against the written briefs and the approved blueprint only.

## 27. Phase 3 handoff and exact commands

`GET /api/v1/intake/{id}/handoff` (409 until confirmed):

```json
{
  "complaint_id": "…",
  "original_text": "The street light near my house has not been working for three days.",
  "language": "en",
  "issue":    {"value": "street light not working", "source_span": "street light near my house has not been working", "source": "citizen_statement", "method": "lexicon", "quality": "clear"},
  "location": {"value": "near my house", "source_span": "near my house", "source": "citizen_statement", "method": "rule", "quality": "clear"},
  "duration": {"value": "5 days", "source_span": "5 days", "source": "citizen_correction", "method": "citizen", "quality": "clear"},
  "entities": [],
  "evidence": [{"field": "issue", "value": "…", "evidence": "…", "source": "…", "method": "…"}],
  "translated_text": null,
  "confirmation_status": "CONFIRMED",
  "processing_mode": "OFFLINE_RULE"
}
```

Phase 3 should read only confirmed handoffs, treat `quality: vague` locations as
needing refinement, and fill `category_required_fields`.

```bash
cp .env.example .env                                   # keys may stay blank
cd backend && python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements-dev.txt
pytest && ruff check app tests ../scripts              # 136 passed
uvicorn app.main:app --reload --port 8000              # http://localhost:8000/docs
python ../scripts/demo_intake.py                       # 10/10 offline demos
python ../scripts/demo_intake.py --base-url http://localhost:8000
cd ../frontend && npm ci && npm test && npm run typecheck && npm run lint && npm run build
npm run dev                                            # http://localhost:5173
../scripts/check_secrets.sh
```
