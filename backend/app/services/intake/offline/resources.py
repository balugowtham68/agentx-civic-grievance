"""Typed loader for the offline intake resources (backend/resources/intake/*.json).

Each language file is structured civic-language knowledge, not code: issue
subjects and problem phrases, number words and duration units, place nouns,
possessives and postpositions/prepositions, identifier markers, Latin-script
marker words for detecting romanised text, correction/confirmation phrases and
clarification question templates. Add or improve a language by editing its file.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, model_validator

RESOURCES_DIR = Path(__file__).resolve().parents[4] / "resources" / "intake"


class PhraseEntry(BaseModel):
    value: str  # English gloss (or id for subjects/states)
    patterns: list[str] = Field(min_length=1)


class DurationUnit(BaseModel):
    unit: Literal["hour", "day", "week", "month", "year"]
    patterns: list[str] = Field(min_length=1)


class QuestionTemplates(BaseModel):
    issue: str
    location: str
    duration: str
    # Optional variant that restates the understood issue, e.g. English:
    # "I understood: {issue}. Where is this?" ({issue} is the English issue value.)
    location_with_issue: str | None = None


class IntakeResources(BaseModel):
    language: str
    note: str = ""
    number_words: dict[str, int] = Field(default_factory=dict)
    duration_units: list[DurationUnit] = Field(default_factory=list)
    duration_particles: list[str] = Field(default_factory=list)  # e.g. Hindi "से" after the unit
    issue_subjects: list[PhraseEntry] = Field(default_factory=list)
    problem_states: list[PhraseEntry] = Field(default_factory=list)
    place_nouns: list[PhraseEntry] = Field(default_factory=list)
    generic_places: list[str] = Field(default_factory=list)  # place values that are vague on their own
    possessives: list[PhraseEntry] = Field(default_factory=list)
    proximity: list[PhraseEntry] = Field(default_factory=list)
    particles: list[str] = Field(default_factory=list)  # joined to a location but not glossed
    identifier_markers: list[str] = Field(default_factory=list)
    latin_markers: list[str] = Field(default_factory=list)  # English function words / romanised words
    correction_phrases: list[str] = Field(default_factory=list)
    confirmation_phrases: list[str] = Field(default_factory=list)
    questions: QuestionTemplates
    location_style: Literal["preposition", "postposition"] = "postposition"

    @model_validator(mode="after")
    def _numbers_positive(self) -> "IntakeResources":
        if any(n <= 0 for n in self.number_words.values()):
            raise ValueError("number_words must map to positive integers")
        return self


class SafetyResources(BaseModel):
    instruction_like_phrases: list[str]


class ResourceError(RuntimeError):
    pass


def load_resources(directory: Path = RESOURCES_DIR) -> dict[str, IntakeResources]:
    resources: dict[str, IntakeResources] = {}
    for path in sorted(directory.glob("*.json")):
        if path.stem == "safety":
            continue
        try:
            data = IntakeResources(**json.loads(path.read_text(encoding="utf-8")))
        except (ValueError, TypeError) as exc:
            raise ResourceError(f"Invalid intake resource {path.name}: {exc}") from exc
        if data.language != path.stem:
            raise ResourceError(f"{path.name} declares language {data.language!r}")
        resources[data.language] = data
    if "en" not in resources:
        raise ResourceError("English intake resources (en.json) are required")
    return resources


def load_safety(directory: Path = RESOURCES_DIR) -> SafetyResources:
    return SafetyResources(**json.loads((directory / "safety.json").read_text(encoding="utf-8")))
