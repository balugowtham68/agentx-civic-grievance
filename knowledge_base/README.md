# Knowledge base

Configured civic knowledge used by the Classification & Reasoning Agent (RAG) and by
the SLA and escalation logic.

> **Everything here is demo knowledge-base data** for the fictional
> "Sample Municipal Corporation". It is not real government policy. Replacing it with a
> real municipality's rules requires no code changes.

## Layout

| Folder | Structured config (loaded + validated at startup) | Documents (indexed for RAG in Phase 3) |
| --- | --- | --- |
| `departments/` | `departments.json` | department charters (`*.md`) |
| `jurisdictions/` | `jurisdictions.json` (wards, localities, landmarks) | ward notes (`*.md`) |
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

Pipeline (Phase 3): documents → chunking by section → embeddings → ChromaDB → retrieval →
classification/reasoning. The classifier may only choose IDs that appear in a retrieved
document's `config_refs`.
