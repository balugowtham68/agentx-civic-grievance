"""Configured civic reference data: civic categories, departments, jurisdictions,
SLA policies (reference only), escalation policies and authorities.

These are loaded from `knowledge_base/` JSON files (demo configuration for the
hackathon, clearly labelled as such). Decisions made by agents must reference
IDs defined here; nothing is invented. Every file carries a `source` block
(provenance) that is attached to each of its records as `source_id`.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.schemas.enums import AuthorityStatus, ComplaintStatus, SLAStage

ID_PATTERN = r"^[A-Z0-9][A-Z0-9_-]{1,63}$"
CATEGORY_PATTERN = r"^[a-z][a-z0-9_]{1,40}$"
LANGUAGE_KEY_PATTERN = r"^[a-z]{2,3}$"
# Facts a category may require or list as optional. Personal data is deliberately absent.
REQUIRED_FIELD_NAMES = {"issue", "location"}
OPTIONAL_FIELD_NAMES = {
    "duration", "landmark", "pole_identifier", "frequency", "waste_type", "severity",
    "visible_flow", "affected_area",
}


class SourceInfo(BaseModel):
    """Provenance of a knowledge-base file. Prototype data must say so."""

    id: str = Field(pattern=ID_PATTERN)
    name: str = Field(min_length=3, max_length=200)
    type: Literal["prototype_configuration", "official_source", "document"]
    version: str = Field(min_length=1, max_length=40)
    official: bool = False
    label: str | None = Field(default=None, max_length=60)

    @model_validator(mode="after")
    def _prototype_is_not_official(self) -> "SourceInfo":
        if self.type == "prototype_configuration" and self.official:
            raise ValueError(f"source {self.id}: prototype configuration cannot be marked official")
        return self


class Department(BaseModel):
    id: str = Field(pattern=ID_PATTERN)
    name: str
    description: str
    categories: list[str] = Field(min_length=1)
    source_id: str | None = None


class Jurisdiction(BaseModel):
    id: str = Field(pattern=ID_PATTERN)
    name: str
    type: str = "ward"
    localities: list[str] = Field(default_factory=list)
    landmarks: list[str] = Field(default_factory=list)
    # Other spellings (six languages, romanised) of a locality or landmark. Keys must be
    # one of `localities` or `landmarks`.
    aliases: dict[str, list[str]] = Field(default_factory=dict)
    source_id: str | None = None

    @model_validator(mode="after")
    def _aliases_name_known_places(self) -> "Jurisdiction":
        known = set(self.localities) | set(self.landmarks)
        unknown = sorted(set(self.aliases) - known)
        if unknown:
            raise ValueError(f"jurisdiction {self.id}: aliases for unknown places {unknown}")
        return self

    def places(self) -> list[tuple[str, str, list[str]]]:
        """(canonical name, kind, spellings incl. the name itself)."""
        return [
            (name, kind, [name, *self.aliases.get(name, [])])
            for kind, names in (("locality", self.localities), ("landmark", self.landmarks))
            for name in names
        ]


class CivicCategory(BaseModel):
    """One civic category record (DEMO CIVIC RULE unless its source is official)."""

    id: str = Field(pattern=ID_PATTERN)
    category: str = Field(pattern=CATEGORY_PATTERN)
    display_name: str = Field(min_length=3, max_length=80)
    display_names: dict[str, str] = Field(default_factory=dict)
    description: str = Field(min_length=10, max_length=600)
    issue_patterns: dict[str, list[str]] = Field(min_length=1)
    aliases: list[str] = Field(default_factory=list)
    department_id: str = Field(pattern=ID_PATTERN)
    jurisdiction_type: str = "ward"
    jurisdiction_required: bool = True
    required_fields: list[str] = Field(min_length=1)
    location_precision: Literal["any", "specific"] = "specific"
    optional_fields: list[str] = Field(default_factory=list)
    service_guideline: str = Field(min_length=5, max_length=400)
    service_timeline_id: str | None = None  # reference data only (SLA is a later phase)
    guideline_doc_ids: list[str] = Field(default_factory=list)
    suppresses: list[str] = Field(default_factory=list)
    active: bool = True
    source_id: str | None = None

    @field_validator("issue_patterns")
    @classmethod
    def _patterns(cls, value: dict[str, list[str]]) -> dict[str, list[str]]:
        for language, patterns in value.items():
            if not language.isalpha() or not 2 <= len(language) <= 3:
                raise ValueError(f"invalid language key {language!r}")
            if not patterns or any(not p.strip() or len(p) > 80 for p in patterns):
                raise ValueError(f"issue_patterns[{language}] must be non-empty phrases of at most 80 characters")
        return value

    @model_validator(mode="after")
    def _fields(self) -> "CivicCategory":
        if not set(self.required_fields) <= REQUIRED_FIELD_NAMES or "issue" not in self.required_fields:
            raise ValueError(f"category {self.id}: required_fields must include 'issue' and use {sorted(REQUIRED_FIELD_NAMES)}")
        if not set(self.optional_fields) <= OPTIONAL_FIELD_NAMES:
            raise ValueError(f"category {self.id}: unknown optional_fields {sorted(set(self.optional_fields) - OPTIONAL_FIELD_NAMES)}")
        return self

    def name_in(self, language: str) -> str:
        return self.display_names.get(language, self.display_name)

    def phrases(self) -> list[tuple[str, str]]:
        """(language, phrase) for every configured pattern, alias and display name."""
        found = [(lang, p) for lang, patterns in self.issue_patterns.items() for p in patterns]
        found += [("en", a) for a in self.aliases]
        found += [("en", self.display_name)] + [(lang, n) for lang, n in self.display_names.items()]
        return found


class AmbiguityGroup(BaseModel):
    """A vague description that fits several categories; the citizen must choose."""

    id: str = Field(pattern=ID_PATTERN)
    terms: dict[str, list[str]] = Field(min_length=1)
    categories: list[str] = Field(min_length=2)
    question: dict[str, str]
    source_id: str | None = None

    @model_validator(mode="after")
    def _english_question(self) -> "AmbiguityGroup":
        if "en" not in self.question:
            raise ValueError(f"ambiguity group {self.id}: an English question is required")
        return self


class RetrievalSettings(BaseModel):
    top_k: int = Field(default=8, ge=1, le=20)
    min_similarity: float = Field(default=0.2, ge=0.0, le=1.0)
    suggestion_similarity: float = Field(default=0.3, ge=0.0, le=1.0)
    max_suggestions: int = Field(default=3, ge=2, le=5)
    max_query_chars: int = Field(default=2000, ge=100, le=5000)


class ClassificationSettings(BaseModel):
    retrieval: RetrievalSettings = Field(default_factory=RetrievalSettings)
    vague_location_phrases: dict[str, list[str]] = Field(default_factory=dict)
    # Question templates per kind (locality | category | unsupported) and language.
    questions: dict[str, dict[str, str]]
    source_id: str | None = None

    @model_validator(mode="after")
    def _templates(self) -> "ClassificationSettings":
        for kind in ("locality", "category", "unsupported"):
            if "en" not in self.questions.get(kind, {}):
                raise ValueError(f"classification settings: an English '{kind}' question is required")
        return self


class Authority(BaseModel):
    """A human authority an escalation can be handed to."""

    id: str = Field(pattern=ID_PATTERN)
    title: str
    jurisdiction_id: str | None = None
    department_id: str | None = None
    source_id: str | None = None


class SLAPolicy(BaseModel):
    id: str = Field(pattern=ID_PATTERN)
    category: str
    department_id: str
    duration_hours: int = Field(gt=0)
    warning_after_hours: int = Field(gt=0)
    source_id: str | None = None

    @model_validator(mode="after")
    def _warning_before_deadline(self) -> "SLAPolicy":
        if self.warning_after_hours >= self.duration_hours:
            raise ValueError("warning_after_hours must be less than duration_hours")
        return self


class EscalationTrigger(BaseModel):
    """When a policy fires. All conditions must hold."""

    source_statuses: list[ComplaintStatus] = Field(
        default_factory=lambda: [ComplaintStatus.BREACHED]
    )
    sla_condition: SLAStage = SLAStage.BREACHED


class EscalationLevel(BaseModel):
    level: int = Field(ge=1)
    target_authority_id: str
    # Extra time after the previous level before this level may fire (0 = immediately).
    after_hours: int = Field(default=0, ge=0)


def _default_terminal_states() -> list[AuthorityStatus]:
    # ACKNOWLEDGED is deliberately absent: ACKNOWLEDGED != RESOLVED.
    return [AuthorityStatus.RESOLVED, AuthorityStatus.CLOSED]


class EscalationPolicy(BaseModel):
    id: str = Field(pattern=ID_PATTERN)
    name: str
    enabled: bool = True
    categories: list[str] = Field(min_length=1)
    trigger: EscalationTrigger = Field(default_factory=EscalationTrigger)
    levels: list[EscalationLevel] = Field(min_length=1)
    # Authority statuses that stop the SLA and block escalation.
    terminal_states: list[AuthorityStatus] = Field(default_factory=_default_terminal_states)
    source_id: str | None = None

    @model_validator(mode="after")
    def _levels_are_sequential(self) -> "EscalationPolicy":
        numbers = [lvl.level for lvl in self.levels]
        if numbers != list(range(1, len(numbers) + 1)):
            raise ValueError("escalation levels must be numbered 1..n in order")
        if not self.terminal_states:
            raise ValueError("terminal_states cannot be empty")
        return self


class ReferenceData(BaseModel):
    """Everything loaded from knowledge_base/ config files, cross-validated."""

    departments: list[Department]
    jurisdictions: list[Jurisdiction]
    authorities: list[Authority]
    sla_policies: list[SLAPolicy]
    escalation_policies: list[EscalationPolicy]
    # Phase 3 - Classification & Reasoning.
    categories: list[CivicCategory] = Field(default_factory=list)
    ambiguity_groups: list[AmbiguityGroup] = Field(default_factory=list)
    classification: ClassificationSettings | None = None
    sources: dict[str, SourceInfo] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _references_exist(self) -> "ReferenceData":
        dept_ids = {d.id for d in self.departments}
        jur_ids = {j.id for j in self.jurisdictions}
        auth_ids = {a.id for a in self.authorities}
        problems: list[str] = []
        for policy in self.sla_policies:
            if policy.department_id not in dept_ids:
                problems.append(f"SLA policy {policy.id}: unknown department {policy.department_id}")
        for auth in self.authorities:
            if auth.jurisdiction_id and auth.jurisdiction_id not in jur_ids:
                problems.append(f"Authority {auth.id}: unknown jurisdiction {auth.jurisdiction_id}")
            if auth.department_id and auth.department_id not in dept_ids:
                problems.append(f"Authority {auth.id}: unknown department {auth.department_id}")
        for esc in self.escalation_policies:
            for lvl in esc.levels:
                if lvl.target_authority_id not in auth_ids:
                    problems.append(
                        f"Escalation policy {esc.id}: unknown authority {lvl.target_authority_id}"
                    )
        problems += self._duplicates()
        problems += self._category_problems(dept_ids)
        if problems:
            raise ValueError("; ".join(problems))
        return self

    def _duplicates(self) -> list[str]:
        problems: list[str] = []
        lists: dict[str, list[str]] = {
            "department": [d.id for d in self.departments],
            "jurisdiction": [j.id for j in self.jurisdictions],
            "authority": [a.id for a in self.authorities],
            "SLA policy": [p.id for p in self.sla_policies],
            "escalation policy": [p.id for p in self.escalation_policies],
            "category record": [c.id for c in self.categories],
            "category": [c.category for c in self.categories],
            "ambiguity group": [g.id for g in self.ambiguity_groups],
        }
        for kind, ids in lists.items():
            dupes = sorted({i for i in ids if ids.count(i) > 1})
            if dupes:
                problems.append(f"duplicate {kind} id(s): {', '.join(dupes)}")
        return problems

    def _category_problems(self, dept_ids: set[str]) -> list[str]:
        problems: list[str] = []
        keys = {c.category for c in self.categories}
        departments = {d.id: d for d in self.departments}
        slas = {p.id: p for p in self.sla_policies}
        for cat in self.categories:
            if cat.department_id not in dept_ids:
                problems.append(f"Category {cat.id}: unknown department {cat.department_id}")
            elif cat.category not in departments[cat.department_id].categories:
                problems.append(f"Category {cat.id}: department {cat.department_id} does not list '{cat.category}'")
            if cat.service_timeline_id:
                sla = slas.get(cat.service_timeline_id)
                if sla is None:
                    problems.append(f"Category {cat.id}: unknown service timeline {cat.service_timeline_id}")
                elif sla.category != cat.category or sla.department_id != cat.department_id:
                    problems.append(f"Category {cat.id}: service timeline {sla.id} is for another category/department")
            for other in cat.suppresses:
                if other not in keys:
                    problems.append(f"Category {cat.id}: suppresses unknown category '{other}'")
        for group in self.ambiguity_groups:
            for key in group.categories:
                if key not in keys:
                    problems.append(f"Ambiguity group {group.id}: unknown category '{key}'")
        if self.categories:
            if self.classification is None:
                problems.append("classification settings are missing")
            records = [*self.categories, *self.departments, *self.jurisdictions, *self.ambiguity_groups]
            for record in records:
                if not record.source_id or record.source_id not in self.sources:
                    problems.append(f"{record.id}: missing provenance (source)")
        return problems

    def category(self, key: str) -> CivicCategory | None:
        return next((c for c in self.categories if c.category == key and c.active), None)

    def active_categories(self) -> list[CivicCategory]:
        return [c for c in self.categories if c.active]
