---
doc_id: KB-RULE-WATER-01
type: civic_rule
config_refs: [CAT-WATER-LEAKAGE, CAT-WATER-SUPPLY, DEPT-WATER, SLA-WATER-LEAKAGE, SLA-WATER-SUPPLY]
demo_data: true
---

# Water leaks and supply interruptions (demo rule)

> DEMO CIVIC RULE for the fictional Sample Municipal Corporation. Not a real government rule.

Two different grievances are handled by the Water Supply Department (`DEPT-WATER`):

- **Water leakage**: water leaking from a public pipeline, a burst pipe, or treated water
  flowing onto the road.
- **Water supply interruption**: no piped water, very low pressure, or supply stopped for an area.

A general "water problem" is not enough to tell them apart (it may also be a drainage
problem), so the citizen is asked which one it is.

## Details a complaint should include

- Street, locality or ward
- Where the water is coming out, or which area has no supply
- Since when (optional)

## Service timeline

Leak repair within 2 days (`SLA-WATER-LEAKAGE`); supply restoration within 1 day (`SLA-WATER-SUPPLY`). Reference data only.
