# Complaint Drafting — SPANDAN AI (Agent 3, DRAFT)

*SPANDAN AI — Listen. Respond. Resolve.*

Phase 4. Turns a complaint that the citizen confirmed (Phase 2) and SPANDAN AI classified
(Phase 3) into a structured administrative complaint draft for the citizen to review, edit and
approve. It adds no facts. Nothing is filed, and no tracking ID, SLA or escalation exists in
this phase.

## 1. Pipeline

```
CLASSIFIED complaint
  -> validate handoff: confirmed Phase 2 handoff (build_handoff) + Phase 3 classification record
  -> DraftFactSet (fact lock): citizen facts + Phase 3 category/department/jurisdiction only
  -> deterministic template draft (config/drafting.json)        always, offline
  -> DraftValidator                                              template must pass
  -> optional AI wording via the existing AIProvider            only rephrasing
  -> DraftValidator + required facts still present              reject -> template draft (FALLBACK_USED)
  -> save version 1 (complaint -> DRAFTING, awaiting review)
  -> citizen edits (new versions, earlier kept) -> citizen approves (complaint -> DRAFTED)
```

Code: `app/agents/drafting/` (`facts.py` fact lock, `builder.py` templates, `validator.py`,
`agent.py`, `config.py`), `app/services/drafting/service.py` (state, versions, audit),
`app/api/routes/drafting.py`, `app/prompts/drafting.py`, `config/drafting.json`.

## 2. Fact lock (`DraftFactSet`)

The draft is built from this set only:

- **Citizen facts:** `original_text`, `citizen_language`, and `issue`, `location` and
  `duration`, each as an English value plus the citizen's own words and source (statement or
  correction). Also locality and category answers given to Phase 3 (attributed as
  `citizen_clarification`) and identifiers (e.g. "pole no. 14").
- **From Phase 3 (locked):**
  - `category`, `category_record_id` and `category_name`
  - `department_id` and `department_name`
  - `jurisdiction_id` and `jurisdiction_name`
  - `resolved_place`, `location_precision`, `source_ids` and `safety_flags`

Before building, drafting checks the Phase 3 result against the knowledge base:

- The category is active.
- The department exists and is the configured mapping.
- The jurisdiction exists, and is resolved when the category requires it.
- The citizen evidence is not empty.

It does not re-classify anything.

## 3. Templates (`config/drafting.json`)

- **Categories:** one template per configured category (streetlight, garbage, water leakage,
  water supply, drainage, road damage, sanitation, broken infrastructure).
- **Wording:** subject, summary and issue label vary by the Phase 2 English issue state (e.g.
  "not working", "not collected", "blocked"), with a neutral default.
- **Content:** templates hold wording only — no numbers, names, departments or wards (tested).
  Placeholders are limited to `{location}` and `{duration}`.
- **Duration:** inserted only if the citizen gave one.

## 4. Location handling

The draft keeps three things apart:

- **The citizen's words:** "As described by the citizen: “on Main Road”". Non-English
  locations are quoted in the citizen's script, not translated.
- **Answers to Phase 3 questions:** "area given by the citizen when asked: “Gandhi Nagar”".
- **The Phase 3 match:** "Matched to Main Road, Ward 7 (demo) (WARD-7) in the prototype
  jurisdiction configuration".

No address, ward, municipality or coordinates are ever added.

## 5. Validation (`DraftValidator`)

The validator is deterministic and fails closed. It sorts draft text into four kinds of
content:

- **A. Exact citizen facts:** the citizen's own words.
- **B. Normalised citizen facts:** Phase 2 values, and numbers written as digits or as
  number words in the six languages.
- **C. Safe administrative wording:** the configured templates, the builder's fixed
  phrases and a small configured `administrative_vocabulary` ("reportedly", "kindly").
- **D. Unsupported new content:** anything else.

Two modes decide what happens.

**Generated text (templates and optional AI)** is rejected (the template draft is used and
`FALLBACK_USED` recorded) when it contains any of:

- a tracking ID (`CIV-YYYY-N`)
- a claim that the complaint was filed, resolved, or acted on by the government
- another configured department, ward or category
- empty or oversized text
- a cause, severity, date, official, evidence or attachment, legal claim or number of
  affected people that the citizen did not state
- new numbers, emails or phone numbers
- **any D-type word**

The last check makes paraphrased inventions fail closed even when they avoid every
configured phrase. For example, "the wiring gave way" or "replace the bulb" are rejected.

**Citizen edits** may add genuine information, for example "It was repaired previously but
stopped working again." Such edits are **not rejected**:

- New claims and new words are listed in `citizen_added_information` as *added by the
  citizen, not verified*.
- The version is saved as `NEEDS_REVIEW` and the locked facts are unchanged.
- The Phase 2 and Phase 3 evidence is never modified.

Only statements that contradict the system stay hard errors (422 `draft_edit_rejected`):
tracking IDs, claims that the complaint was filed, and another department, ward or category.

The verbatim citizen statement is citizen data, not draft text, so it is not validated. It
is left out of the body when Phase 2 flagged instruction-like text.

**Validation status:**

- `VALID`
- `FALLBACK_USED`: AI wording rejected or failed; template used.
- `NEEDS_REVIEW`: a citizen edit added unverified information.
- `INVALID`: never stored.

There are no confidence scores.

## 6. Optional AI

The optional AI uses the existing `AIProvider` (`build_ai_provider`); there is no new client.

- **Prompt `drafting.compose/v1`:**
  - citizen text is untrusted data
  - knowledge-base text is reference data only
  - the Phase 3 classification is authoritative
  - only the given facts may be included
  - no filing, resolution or inspection claims
  - output is schema-validated JSON
- **When the AI output is dropped:** a provider failure, timeout, malformed output or any
  validation problem means the template draft is used, `FALLBACK_USED` is recorded, and the
  reasons are audited.
- **When it is accepted:** `processing_mode: MIXED`.
- **Locked fields:** category, department and jurisdiction are never part of the AI output.

## 7. States

`CLASSIFIED → DRAFTING` (draft v1 generated, awaiting review) `→ DRAFTED` (citizen approved a
specific version; `approved_version` in the view).

Editing an approved draft withdraws the approval:

- The complaint goes back to `DRAFTED → DRAFTING`.
- The approved version is kept unchanged but marked `SUPERSEDED`.
- `drafting.approval_withdrawn` is audited.
- The Phase 5 payload `complaints.drafted_complaint` is cleared until the next approval. There is no
`UNDERSTOOD → DRAFTED`, `CLASSIFIED → DRAFTED`, `CLASSIFIED → FILED` or `DRAFTED → RESOLVED`.
A `NEEDS_INFO`, `AMBIGUOUS` or unsupported classification is never drafted (409 with the reason).

## 8. API (`/api/v1/drafting`)

| Method | Path | Result |
| --- | --- | --- |
| POST | `/{id}/run` | 201 `DraftView` (v1). 409 `intake_not_confirmed` / `complaint_not_classified`, 422 `classification_incomplete` / `draft_validation_failed`; optional `{draft_language}` (only `en` offline; other languages get an English draft with a note) |
| GET | `/{id}` | Current version + version history |
| GET | `/{id}/versions/{n}` | A specific version |
| POST | `/{id}/edit` | `{based_on_version, subject?, summary?, issue_text?, location_text?, duration_text?, requested_action?}` → new version; 409 on a stale version; 422 `draft_edit_rejected` for hard issues. Category, department and jurisdiction are not accepted fields |
| POST | `/{id}/approve` | `{version}` (latest only) → complaint `DRAFTED`; fills `complaints.drafted_complaint` (the Phase 5 filing payload). Nothing is filed |

## 9. Persistence and audit

Table `complaint_drafts`: one row per version, unique `(complaint_id, version)`. Each row
holds:

- `origin`, `based_on_version`
- `subject`, `body`
- the languages, `processing_mode`, `validation_status`, `review_status`, `source_ids`
- the full draft snapshot and the fact set it was built from
- `created_by`, timestamps

Phase 2 and Phase 3 records and the complaint's original text are never modified.

Audit events: `drafting.started`, `drafting.source_loaded`, `drafting.generated`,
`drafting.validation_passed`, `drafting.validation_failed`, `drafting.fallback` (template used
instead of AI wording), `drafting.edited` (citizen), `drafting.version_created`,
`drafting.approved` (citizen, with version), `drafting.approval_withdrawn`, `drafting.completed`
and `complaint.drafted`.
Payloads hold ids, versions, statuses and field names — no citizen text, prompts or keys.

## 10. Languages

English drafting works offline. Complaints in Tamil, Telugu, Hindi, Kannada and Malayalam get
an English draft (`draft_language: "en"`) that quotes the citizen's own words (location, issue,
duration and the full statement) with a note that no machine translation was made. Citizens can
edit any section in their own language (Unicode, including zero-width joiners, is kept exactly);
such words are marked as citizen-added. Native-language generated drafting is not implemented:
no reliable local translation model is available offline, and a fabricated translation would be
worse than a safe English draft plus the original words.
