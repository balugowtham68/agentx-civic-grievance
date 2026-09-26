"""Read-only access to configured civic reference data in knowledge_base/.

Files (JSON, demo configuration):
    departments/departments.json
    jurisdictions/jurisdictions.json
    escalation/authorities.json
    timelines/sla_policies.json
    escalation/escalation_policies.json
    categories/categories.json              (Phase 3)
    categories/ambiguity_groups.json        (Phase 3)
    categories/classification_settings.json (Phase 3)

Each file may carry a `source` block (provenance); its id is attached to every
record of that file as `source_id`. Loaded once and cross-validated; a broken reference fails at startup rather
than during the demo.
"""

from __future__ import annotations

import json
from functools import cached_property
from pathlib import Path
from typing import Any

from app.core.errors import NotFoundError
from app.schemas.reference import (
    Authority,
    CivicCategory,
    Department,
    EscalationPolicy,
    Jurisdiction,
    ReferenceData,
    SLAPolicy,
)

REFERENCE_FILES = {
    "departments": Path("departments/departments.json"),
    "jurisdictions": Path("jurisdictions/jurisdictions.json"),
    "authorities": Path("escalation/authorities.json"),
    "sla_policies": Path("timelines/sla_policies.json"),
    "escalation_policies": Path("escalation/escalation_policies.json"),
    "categories": Path("categories/categories.json"),
    "ambiguity_groups": Path("categories/ambiguity_groups.json"),
}
CLASSIFICATION_SETTINGS_FILE = Path("categories/classification_settings.json")


class ReferenceDataError(RuntimeError):
    pass


class ReferenceRepository:
    def __init__(self, knowledge_base_dir: Path) -> None:
        self.root = knowledge_base_dir

    def _load(self, relative: Path) -> dict[str, Any]:
        path = self.root / relative
        if not path.exists():
            raise ReferenceDataError(f"Missing reference file: {path}")
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ReferenceDataError(f"Invalid JSON in {path}: {exc}") from exc
        if not isinstance(data, dict):
            raise ReferenceDataError(f"{path} must be a JSON object")
        return data

    def _read(self, relative: Path, sources: dict[str, Any]) -> list[dict[str, Any]]:
        data = self._load(relative)
        items = data.get("items")
        if not isinstance(items, list) or not all(isinstance(i, dict) for i in items):
            raise ReferenceDataError(f"{self.root / relative} must be an object with an 'items' list of objects")
        source = data.get("source")
        if isinstance(source, dict) and isinstance(source.get("id"), str):
            sources[source["id"]] = source
            items = [{**item, "source_id": item.get("source_id", source["id"])} for item in items]
        return items

    @cached_property
    def data(self) -> ReferenceData:
        sources: dict[str, Any] = {}
        try:
            values: dict[str, Any] = {key: self._read(rel, sources) for key, rel in REFERENCE_FILES.items()}
            settings = self._load(CLASSIFICATION_SETTINGS_FILE)
            source = settings.get("source")
            if isinstance(source, dict) and isinstance(source.get("id"), str):
                sources[source["id"]] = source
                settings = {**settings, "source_id": source["id"]}
            values["classification"] = {k: v for k, v in settings.items() if k not in {"_note", "source"}}
            return ReferenceData(**values, sources=sources)
        except ValueError as exc:
            raise ReferenceDataError(f"Invalid reference data: {exc}") from exc

    def _find(self, items: list[Any], item_id: str, kind: str) -> Any:
        for item in items:
            if item.id == item_id:
                return item
        raise NotFoundError(f"{kind} {item_id!r} is not configured")

    def department(self, department_id: str) -> Department:
        return self._find(self.data.departments, department_id, "Department")

    def jurisdiction(self, jurisdiction_id: str) -> Jurisdiction:
        return self._find(self.data.jurisdictions, jurisdiction_id, "Jurisdiction")

    def authority(self, authority_id: str) -> Authority:
        return self._find(self.data.authorities, authority_id, "Authority")

    def sla_policy(self, policy_id: str) -> SLAPolicy:
        return self._find(self.data.sla_policies, policy_id, "SLA policy")

    def category(self, category: str) -> CivicCategory:
        found = self.data.category(category)
        if found is None:
            raise NotFoundError(f"Category {category!r} is not configured")
        return found

    def escalation_policy_for_category(self, category: str) -> EscalationPolicy | None:
        for policy in self.data.escalation_policies:
            if policy.enabled and category in policy.categories:
                return policy
        return None
