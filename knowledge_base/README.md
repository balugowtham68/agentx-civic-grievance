# Knowledge base

Configured civic knowledge used by the Classification & Reasoning Agent (RAG) and by
the SLA and escalation logic.

> **Everything here is DEMO CIVIC RULE / PROTOTYPE CONFIGURATION** for the fictional
> "Sample Municipal Corporation". It is not real government policy. Every JSON file carries a
> `source` block (`type: prototype_configuration`, `official: false`); a prototype source
> cannot be marked official. Replacing it with a real municipality's rules requires no code
> changes. Non-English phrases are drafts pending native-speaker review.

## Layout

| Folder | Structured config (loaded + validated at startup) | Documents (indexed for RAG in Phase 3) |
| --- | --- | --- |
| `categories/` | `categories.json`, `ambiguity_groups.json`, `classification_settings.json` (Phase 3) | — |
| `departments/` | `departments.json` | department charters (`*.md`) |
| `jurisdictions/` | `jurisdictions.json` (PROTOTYPE JURISDICTION CONFIGURATION: wards, localities, landmarks, aliases) | ward notes (`*.md`) |
| `rules/` | — | civic rules, one per grievance type (`*.md`) |
| `timelines/` | `sla_policies.json` | service timeline notes (`*.md`) |
| `escalation/` | `authorities.json`, `escalation_policies.json` | escalation hierarchy notes (`*.md`) |

## JSON config format

Each JSON file is `{"_note": "...", "items": [ ... ]}`. Item schemas are the Pydantic
models in `backend/app/schemas/reference.py`. IDs are upper-case (`DEPT-ELECTRICAL`,
`WARD-12`). Cross-references are checked at startup; a broken reference stops the backend
with a clear error.

Escalation policies list `terminal_states` — the authority statuses that stop the SLA and
block escalation. The default is `RESOLVED` and `CLOSED`. **ACKNOWLEDGED is not
terminal** (acknowledged ≠ resolved).

## Markdown document format (RAG)

```markdown
---
doc_id: KB-RULE-STREETLIGHT-01      # unique, cited as evidence
type: civic_rule                     # civic_rule | department | jurisdiction | timeline | guideline | escalation
config_refs: [DEPT-ELECTRICAL, SLA-STREETLIGHT]   # config IDs this document supports
demo_data: true
---
# Title
Body in short sections.
```

Pipeline (Phase 3, implemented): records and documents → chunks (category summary + phrases
per language, one per `## ` section) → local hashing n-gram embeddings → local ChromaDB →
top-k retrieval with metadata filters → configured rule validation → classification.
Only configured category, department and jurisdiction IDs can be chosen.

Ingest / validate: `python scripts/ingest_civic_kb.py` (`--check` to validate only).
See [`docs/classification.md`](../docs/classification.md).
