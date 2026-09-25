---
doc_id: KB-RULE-STREETLIGHT-01
type: civic_rule
config_refs: [DEPT-ELECTRICAL, SLA-STREETLIGHT]
demo_data: true
---

# Non-working streetlights (demo rule)

> Demo knowledge-base data for the fictional Sample Municipal Corporation. Not a real rule.

A streetlight that does not switch on at night, flickers, or has a broken fitting is a
**streetlight** grievance. It is handled by the Electrical Maintenance Department
(`DEPT-ELECTRICAL`) of the ward where the pole stands.

## Details a complaint should include

- Nearest landmark or house number, so the pole can be found
- How long the light has not been working
- Pole number, if the citizen can see one (optional)

## Service timeline

Repair within 3 days (`SLA-STREETLIGHT`). A warning is raised after 2 days if the
complaint is not resolved.
