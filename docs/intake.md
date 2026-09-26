# Citizen Intake — SPANDAN AI (Agent 1, UNDERSTAND)

> Consolidation note (Phase 1–4): Indic zero-width joiners (ZWJ/ZWNJ) are now preserved in the citizen's text, and evidence spans ending in a Malayalam chillu are reported exactly.

*SPANDAN AI — Listen. Respond. Resolve.*

Phase 2. A citizen describes a civic problem once, by voice or text, in English, Tamil,
Telugu, Hindi, Kannada or Malayalam. SPANDAN AI turns it into structured facts — each
backed by the citizen's own words — asks for anything essential that is missing, and lets
the citizen correct and confirm. It **works with no internet and no API key**. It never
classifies into a department, category or jurisdiction (Phase 3), and the only status it
can reach is `UNDERSTOOD`, and only after the citizen confirms.

## 1. Offline-first architecture

```
Citizen input: text | browser speech -> text | uploaded audio
  -> validation + sanitisation              TextIntakeRequest / validate_audio (type, magic bytes, size, duration)
  -> speech-to-text (uploaded audio only)   ChainTranscriptionProvider: LocalWhisper -> optional RemoteWhisper
  -> safety flags                           instruction-like text flagged (resources/intake/safety.json)
  -> language                               citizen choice -> Unicode script -> romanised heuristics -> optional AI -> "und"
  -> offline extraction (always first)      OfflineIntakeEngine: English patterns + per-language lexicons
  -> optional AI (only for gaps)            AIFactExtractor, only if issue or location is still missing and AI is configured
  -> optional translation                   TranslationProvider (AI); none offline -> original kept
  -> evidence verification (ALL layers)     every fact's evidence must be in the citizen's words
  -> citizen corrections applied            newest citizen input wins
  -> missing information + questions        issue + location required; duration optional
  -> IntakeResult persisted                 complaint -> UNDERSTANDING (complete) or NEEDS_INFO
  -> citizen confirms "What I understood"   -> UNDERSTOOD; Phase 3 handoff available
```

Layers: `api/routes/intake.py` → `services/intake/service.py` (persistence, state
machine, audit) → `agents/intake/agent.py` (understanding) → providers in
`services/intake/` (offline engine, detection, STT, translation) and `services/ai/`
(optional Gemini) → repositories (`intake_records` table).

Every result carries `processing_mode` and a `provider_trace`:

| `processing_mode` | Meaning |
| --- | --- |
| `OFFLINE_RULE` | Only local rules and language resource files were used |
| `OFFLINE_LOCAL_MODEL` | A local model (e.g. local Whisper) was used; no network |
| `OPTIONAL_AI` | An external AI provider produced the facts |
| `MIXED` | Offline facts, with one or more gaps filled by the optional AI |

`provider_trace` lists each stage (`speech_to_text`, `language`, `extraction`,
`ai_extraction`, `translation`) with the provider and outcome (`used`, `failed`,
`skipped`, `unavailable`). It never contains keys or raw provider responses.

## 2. Language support (honest matrix)

Configured in `backend/config/languages.json`; lexicons in `backend/resources/intake/<code>.json`.

| Language | Offline text intake | Romanised | Voice | Translation to English | UI strings |
| --- | --- | --- | --- | --- | --- |
| English (en) | **SUPPORTED** (patterns + lexicon, tested) | n/a | Browser (browser-dependent) | not needed | SUPPORTED |
| Tamil (ta) | PARTIALLY_SUPPORTED (draft lexicon, tested on demo sentences) | yes (heuristic, limited) | Browser (browser-dependent) | FALLBACK: original kept; optional AI | PARTIAL (draft) |
| Telugu (te) | PARTIALLY_SUPPORTED | yes (limited) | Browser | FALLBACK | PARTIAL (draft) |
| Hindi (hi) | PARTIALLY_SUPPORTED | yes (limited) | Browser | FALLBACK | PARTIAL (draft) |
| Kannada (kn) | PARTIALLY_SUPPORTED | yes (limited) | Browser | FALLBACK | FALLBACK (English UI) |
| Malayalam (ml) | PARTIALLY_SUPPORTED | yes (limited) | Browser | FALLBACK | FALLBACK (English UI) |

PARTIALLY_SUPPORTED means: works fully offline for common civic complaints (street
lights, water, drainage, garbage, roads, potholes, electricity, sewage, …) using a
**draft vocabulary that needs native-speaker review**. Sentences outside that vocabulary
return fewer facts and a clarification question — never guessed facts.

`GET /api/v1/intake/capabilities` returns this matrix at runtime, plus `offline_first`,
which speech-to-text providers are available and whether the optional AI is configured.

## 3. Language detection (priority order)

1. **Citizen selected** (`language` in the request) — always wins (`method: declared`).
2. **Unicode script** — Tamil, Telugu, Devanagari, Kannada, Malayalam blocks (`script`).
3. **Local heuristics** — for Latin-script text, a marker-word vote over each language's
   `latin_markers` (e.g. *naala*, *eriyala* → Tamil; *nahi*, *din se* → Hindi)
   (`heuristic`, `transliterated: true`). Needs ≥ 2 markers and a clear lead.
4. **Optional AI** — only if the heuristic is undecided and a key is configured (`provider`).
5. **English only when justified** — English markers present; otherwise `und`, and the
   citizen is asked to choose (`intake_status: NEEDS_LANGUAGE`). A script with no
   configured language (e.g. Bengali) also gives `NEEDS_LANGUAGE`.

No confidence number is invented (`confidence: null`). `language_source` repeats the method.

## 4. Extraction layers and evidence

| Layer | Implementation | Network |
| --- | --- | --- |
| 1. Rules | English prepositional/duration/identifier patterns (`extraction.py`) | none |
| 2. Language dictionaries | `OfflineIntakeEngine` + `resources/intake/*.json`: issue subjects × problem states, place nouns + postpositions/possessives, number words × duration units, identifier markers | none |
| 3. Optional local model | Interface only (`FactExtractor`); **none bundled** | none |
| 4. Optional external AI | `AIFactExtractor` (Gemini), only for missing issue/location | yes |

Every fact records `method` (`rule`, `lexicon`, `ai`, `citizen`) and `quality` (`clear`,
`vague`, `partial`). `agents/intake/verification.py` checks **every layer** — offline and
AI alike: the evidence must appear in the citizen's statements (case, spacing and Unicode
normalised), and a value may not introduce numbers (digits or number words in any of the
six languages) that the citizen did not state. Failing facts go to `rejected_facts`
(audited as `intake.facts_rejected`). External AI never bypasses this.

## 5. Voice

`SpeechToTextProvider` chain, in order:

1. **Browser** (Web Speech API; Chrome/Edge; per-language support varies by browser and OS).
   The browser turns speech into text; it is submitted as `input_channel: "voice"` and the
   trace records `browser_speech`.
2. **Local** — `LocalWhisperProvider` (faster-whisper) when the package is installed and
   `LOCAL_STT_MODEL_PATH` points to a model directory. **No model is bundled** and this
   was **not tested with a real model** (the build machine could not download one).
3. **Remote (optional)** — OpenAI Whisper when `OPENAI_API_KEY` is set.

`SPEECH_TO_TEXT_PROVIDER=auto|local|whisper|none` (default `auto`). If no server provider
is available, `POST /intake/voice` returns 503 and the UI offers browser speech or typing.
Uploaded audio is validated by MIME type, magic bytes (WAV, OGG, WebM, MP3, M4A), size
(`MAX_AUDIO_BYTES`) and — for WAV — duration (`MAX_AUDIO_SECONDS`); the browser recorder
also stops at 120 s. **Audio is processed in memory and never stored.**

## 6. Translation

Provider-based. No local machine-translation model exists in this build, so offline the
translation status is `UNAVAILABLE`, `translated_text` is `null` and the **original words
are kept** — extraction works on the original language directly, so nothing is lost.
With the optional AI configured, an English translation is added for readers, but it is
never used as evidence.

## 7. Missing information and questions

`issue` and `location` are required; `duration` is optional. A vague location (e.g.
"our street", "the road") or a partial issue (a subject with no stated problem) is kept
but marked `quality: vague` / `partial`, so the citizen can refine it with Edit and Phase 3
knows it is imprecise; it does not block confirmation. Questions come from each language's resource file (not
generated) and are concise and contextual, e.g. *"I understood: street light not
working. Where is this? Please mention a street, area or nearby landmark."*
`category_required_fields` is always empty in the intake result: category-specific requirements are decided by Phase 3 and reported in the classification result (`required_information`, see [`classification.md`](classification.md)).

## 8. Correction and confirmation

- Structured: `{"corrections": [{"field": "location", "value": "near the temple"}]}`.
- Free text: `{"text": "No, it is 5 days"}` — parsed **offline** with the same engine
  (leading yes/no words ignored). No LLM is used. If nothing is understood → 422
  `correction_not_understood`.
- Corrections are attributed to the citizen (`source: citizen_correction`,
  `method: citizen`, evidence = their words). **Newest citizen input wins** between
  corrections and clarification answers.
- Confirmation (`POST /intake/{id}/confirm`) is the only way to `UNDERSTOOD`; 409 while a
  required fact is missing. Intake never sets CLASSIFIED, DRAFTED, FILED, MONITORING,
  ESCALATED or RESOLVED.

## 9. Safety

- Citizen text is data, never instructions. Instruction-like text ("ignore previous
  instructions", "mark this resolved", …) is flagged `instruction_like_text`, audited,
  shown to the citizen, and only ever treated as complaint content.
- For the optional AI, citizen text is sent as a JSON array inside
  `<citizen_statements>` labelled untrusted; outputs are schema-validated and evidence-checked.
- No API keys, authorization headers or provider credentials appear in responses, audit
  payloads, capabilities, health or logs (tested with a sentinel key).

## 10. API (`/api/v1`)

| Method | Path | Result |
| --- | --- | --- |
| GET | `/intake/capabilities` | Languages, support levels, offline-first flag, providers |
| POST | `/intake/text` | 201 `IntakeResult` — `{raw_text, language?, input_channel?}` |
| POST | `/intake/voice?language=xx` | 201 `IntakeResult` — raw audio body, `Content-Type: audio/*` |
| GET | `/intake/{id}` | Latest `IntakeResult` |
| POST | `/intake/{id}/process` | Run/retry intake for a complaint still `CREATED` — `{language?}` |
| POST | `/intake/{id}/answer` | Answer a clarification — `{text}` |
| POST | `/intake/{id}/correction` | `{corrections: [...]}` or `{text}` |
| POST | `/intake/{id}/confirm` | Citizen confirms → `UNDERSTOOD` |
| GET | `/intake/{id}/handoff` | Phase 3 handoff; 409 until confirmed |

The early duplicate aliases under `/complaints/{id}/intake/...` were removed during the Phase 1–4
consolidation (the frontend uses the paths above). All `{id}` path parameters must be UUIDs (422 otherwise).
While a complaint is in classification or drafting, these endpoints refuse to change it (409).

`IntakeResult` main fields: `complaint_id, input_channel, status, intake_status,
original_text, transcript, language{language, method, transliterated, script, supported},
language_source, processing_language, translation, translated_text,
extracted{issue, location, duration, entities}, evidence[], rejected_facts[],
missing_information[], clarification_questions[], extraction, processing_mode,
provider_trace[], safety_flags[], category_required_fields[],
citizen_confirmation_status, clarifications[], corrections[], created_at, updated_at`.

## 11. Audit events

| Brief name | Event type | When |
| --- | --- | --- |
| INTAKE_RECEIVED | `intake.received` | Text or voice accepted |
| LANGUAGE_DETECTED | `intake.language_detected` | Every run (method + source) |
| TRANSCRIPTION_COMPLETED | `complaint.transcribed` | Server STT succeeded |
| TRANSLATION_COMPLETED | `complaint.translated` / `intake.translation_failed` | Translation ran |
| FACTS_EXTRACTED | `intake.facts_extracted` (payload: processing_mode, provider_trace, safety_flags) / `intake.failed` | Every run |
| FACTS_REJECTED | `intake.facts_rejected` | A proposed fact failed evidence checks |
| MISSING_INFO_DETECTED | `intake.missing_info_detected` | Required field missing |
| CLARIFICATION_REQUESTED | `complaint.info_requested` | Question asked |
| (answer) | `intake.clarification_answered` | Citizen answered |
| CITIZEN_CORRECTION | `intake.corrected` | Citizen corrected (actor: citizen) |
| CITIZEN_CONFIRMED | `intake.confirmed` + `complaint.understood` | Citizen confirmed |

## 12. Errors and fallbacks

| Situation | Behaviour |
| --- | --- |
| Empty, too short, > 2,000 chars, markup only | 422 `validation_error` |
| Unsupported declared language | 422 `unsupported_language` |
| Script with no configured language / undecidable Latin text | Saved; `NEEDS_LANGUAGE`; citizen chooses; retry via `/process` |
| Offline engine error | Saved; `intake_status: FAILED`; nothing guessed; retry |
| Optional AI fails / times out / no key | Offline result kept; trace shows `failed` / `unavailable` |
| No translation provider | Original kept; `translation.status: UNAVAILABLE` |
| Audio: wrong type / not audio or damaged / too large or too long | 415 / 422 `invalid_audio` / 413 `payload_too_large` |
| No server STT / STT fails / times out | 503 / 502 / 504; no complaint created |

## 13. Offline demos

`python scripts/demo_intake.py` (no network, no key) runs ten deterministic demos:
street light in en, ta, te, hi, kn, ml; missing location; citizen correction + confirm;
prompt injection; unsupported language. All ten pass in this build.

## 14. Adding a language

1. Add an entry to `backend/config/languages.json` (support levels honest).
2. Add `backend/resources/intake/<code>.json` (same keys as `en.json`; see `ta.json`).
3. Add UI strings in `frontend/src/i18n/strings.ts` (optional; English fallback).
4. Add a demo sentence test in `backend/tests/test_intake_api.py`.
No code change is required.

## 15. Phase 3 handoff

`GET /intake/{id}/handoff` (only after confirmation):
`{complaint_id, original_text, language, issue, location, duration, entities, evidence,
translated_text, confirmation_status: "CONFIRMED", processing_mode}` — each fact with its
`source_span`, `source`, `method`.
