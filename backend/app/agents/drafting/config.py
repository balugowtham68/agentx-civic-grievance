"""Drafting configuration (backend/config/drafting.json): wording templates per
category and the claim classes a draft may never introduce. Templates contain no
facts; departments and jurisdictions are NOT configured here (they come from Phase 3).
"""

from __future__ import annotations

import json
import string
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, Field, model_validator

DRAFTING_CONFIG_FILE = Path(__file__).resolve().parents[3] / "config" / "drafting.json"
_ALLOWED_PLACEHOLDERS = {"location", "duration"}


class DraftingLimits(BaseModel):
    subject_chars: int = Field(default=160, ge=40, le=300)
    section_chars: int = Field(default=1500, ge=200, le=5000)
    body_chars: int = Field(default=6000, ge=500, le=20000)
    edit_field_chars: int = Field(default=1500, ge=100, le=5000)


class CategoryTemplate(BaseModel):
    subject: dict[str, str]
    summary: dict[str, str]
    issue_label: dict[str, str]
    requested_action: str

    @model_validator(mode="after")
    def _defaults_and_placeholders(self) -> "CategoryTemplate":
        for name in ("subject", "summary", "issue_label"):
            if "default" not in getattr(self, name):
                raise ValueError(f"template {name} needs a 'default' entry")
        texts = [*self.subject.values(), *self.summary.values(), *self.issue_label.values(), self.requested_action]
        for text in texts:
            fields = {f for _, f, _, _ in string.Formatter().parse(text) if f}
            if not fields <= _ALLOWED_PLACEHOLDERS:
                raise ValueError(f"unknown placeholder(s) {sorted(fields - _ALLOWED_PLACEHOLDERS)} in {text!r}")
        return self

    def pick(self, table: dict[str, str], issue_value: str) -> str:
        """The entry whose state label occurs in the Phase 2 issue label, else the default."""
        lowered = issue_value.lower()
        for state, text in sorted(table.items(), key=lambda kv: -len(kv[0])):
            if state != "default" and state in lowered:
                return text
        return table["default"]


class DraftingConfig(BaseModel):
    version: str
    draft_languages: list[str]
    limits: DraftingLimits
    duration_phrase: str
    location_phrase: dict[str, str]
    templates: dict[str, CategoryTemplate]
    forbidden_claims: dict[str, list[str]]
    administrative_vocabulary: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _complete(self) -> "DraftingConfig":
        if "en" not in self.draft_languages:
            raise ValueError("English drafting must be configured")
        if set(self.location_phrase) != {"citizen_english", "citizen_other_language"}:
            raise ValueError("location_phrase needs citizen_english and citizen_other_language")
        return self


@lru_cache(maxsize=4)
def load_drafting_config(path: Path = DRAFTING_CONFIG_FILE) -> DraftingConfig:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return DraftingConfig(**{k: v for k, v in raw.items() if not k.startswith("_")})
