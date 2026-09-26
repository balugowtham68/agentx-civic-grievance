"""Draft validation - the no-hallucination guard for Phase 4.

Deterministic and fail-closed. Every piece of draft text is checked against the
fact-locked DraftFactSet and distinguishes four kinds of content:

  A. exact citizen facts          - the citizen's own words (always allowed)
  B. normalised citizen facts     - Phase 2 values, numbers as digits/number words
  C. safe administrative wording  - the configured templates plus a small configured
                                    administrative vocabulary ("reportedly", "kindly")
  D. unsupported new content      - anything else

Two modes:
- `generated` (templates, optional AI): hard issues and any D content reject the
  text (the template draft is used instead). AI wording must use only A, B and C
  words, so a paraphrased invention ("the wiring gave way") fails closed even if
  it avoids every configured claim phrase.
- `citizen_edit`: the citizen may add genuine information ("it was repaired before
  but stopped working again"). New claims and new words are NOT rejected; they are
  listed as citizen-added, unverified information and the version is NEEDS_REVIEW.
  Only statements that contradict the system itself stay hard errors: tracking IDs,
  claims that the complaint was filed, another department, ward or category
  (those come from Phase 3 and filing does not exist yet).
"""

from __future__ import annotations

import re
import string
from dataclasses import dataclass, field
from functools import cached_property
from typing import Literal

from app.agents.drafting.builder import BUILDER_PHRASES
from app.agents.drafting.config import DraftingConfig
from app.agents.intake.verification import numbers_in
from app.schemas.drafting import DraftFactSet, DraftSections
from app.schemas.reference import ReferenceData
from app.services.intake.offline.text import is_separator, normalise

_TRACKING_ID = re.compile(r"\bCIV-\d{4}-\d+\b", re.IGNORECASE)
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
_PHONE = re.compile(r"(?<!\d)(?:\+?\d[\d\s-]{8,}\d)(?!\d)")
# Claims that are false by construction in Phase 4 whoever writes them.
_SYSTEM_GROUPS = ("filing",)
# Claims a generated draft can never make; a citizen may state them (flagged for review).
_GENERATED_HARD_GROUPS = ("resolution", "filing", "government_action")
_STOPWORDS = frozenset(
    "the and for with from that this these those are was were been being has have had not but its it's "
    "into onto upon than then there their them they you your our any all can may might will would shall "
    "should could does did doing done who whom whose which what when where why how such very also".split()
)
_SUFFIXES = ("ing", "ed", "es", "s", "ly", "al")
Mode = Literal["generated", "citizen_edit"]


@dataclass
class ValidationReport:
    hard: list[str] = field(default_factory=list)  # always rejected
    soft: list[str] = field(default_factory=list)  # rejected for generated text
    citizen_added: list[str] = field(default_factory=list)  # citizen edit: new, unverified information

    @property
    def ok(self) -> bool:
        return not self.hard and not self.soft


def _contains(haystack: str, phrase: str) -> bool:
    needle = normalise(phrase)
    if not needle:
        return False
    return re.search(rf"(?<!\w){re.escape(needle)}", haystack) is not None


def _words(text: str) -> list[str]:
    """Content words (normalised; separators per Phase 2 so all six scripts split correctly)."""
    norm = normalise(text)
    words: list[str] = []
    current: list[str] = []
    for ch in norm + " ":
        if is_separator(ch) and ch != "-":
            if current:
                word = "".join(current).strip("-")
                if len(word) >= 3 and not word.isdigit() and word not in _STOPWORDS:
                    words.append(word)
                current = []
        else:
            current.append(ch)
    return words


def _stem(word: str) -> str:
    for suffix in _SUFFIXES:
        if word.endswith(suffix) and len(word) - len(suffix) >= 4:
            return word[: -len(suffix)]
    return word


class DraftValidator:
    def __init__(self, config: DraftingConfig, data: ReferenceData) -> None:
        self.config = config
        self.data = data

    @cached_property
    def _template_vocabulary(self) -> set[str]:
        texts = list(self.config.administrative_vocabulary)
        for template in self.config.templates.values():
            texts += [*template.subject.values(), *template.summary.values(), *template.issue_label.values(),
                      template.requested_action]
        texts += [self.config.duration_phrase, *self.config.location_phrase.values()]
        formatter = string.Formatter()
        plain = " ".join("".join(lit for lit, *_ in formatter.parse(t)) for t in texts)
        return {_stem(w) for w in _words(plain)}

    def _allowed_words(self, facts: DraftFactSet) -> set[str]:
        return self._template_vocabulary | {_stem(w) for w in _words(" ".join([*facts.locked_texts(), *BUILDER_PHRASES]))}

    def validate(
        self, sections: DraftSections, body: str, facts: DraftFactSet, *, mode: Mode = "generated"
    ) -> ValidationReport:
        """`body` is composed WITHOUT the verbatim citizen statement (citizen data, not draft text)."""
        report = ValidationReport()
        limits = self.config.limits
        values = sections.model_dump()
        for name, text in values.items():
            if not text or not text.strip():
                report.hard.append(f"{name} is empty")
            limit = limits.subject_chars if name == "subject" else limits.section_chars
            if len(text) > limit:
                report.hard.append(f"{name} is longer than {limit} characters")
        if len(body) > limits.body_chars:
            report.hard.append(f"the draft is longer than {limits.body_chars} characters")

        generated = normalise(" \n ".join([*values.values(), body]))
        citizen = normalise(" \n ".join(facts.citizen_texts()))
        locked = normalise(" \n ".join(facts.locked_texts()))
        edit = mode == "citizen_edit"

        if _TRACKING_ID.search(" ".join(values.values()) + body):
            report.hard.append("contains a tracking ID (tracking IDs are issued only by filing, a later phase)")
        for group, phrases in self.config.forbidden_claims.items():
            label = group.replace("_", " ")
            for phrase in phrases:
                if not _contains(generated, phrase):
                    continue
                if group in _SYSTEM_GROUPS or (group in _GENERATED_HARD_GROUPS and not edit):
                    report.hard.append(f"claims {label}: '{phrase.strip()}' (a draft cannot state this)")
                elif _contains(citizen, phrase):
                    continue  # the citizen said it: an exact citizen fact
                elif edit:
                    report.citizen_added.append(f"{label}: '{phrase.strip()}'")
                else:
                    report.soft.append(f"{label} not stated by the citizen: '{phrase.strip()}'")

        for dept in self.data.departments:
            if dept.id != facts.department_id and (_contains(generated, dept.id) or _contains(generated, dept.name)):
                report.hard.append(f"mentions another department ({dept.id}); the department comes from Phase 3")
        for jur in self.data.jurisdictions:
            if jur.id != facts.jurisdiction_id and (_contains(generated, jur.id) or _contains(generated, jur.name)):
                report.hard.append(f"mentions another jurisdiction ({jur.id}); the jurisdiction comes from Phase 3")
        for cat in self.data.active_categories():
            if cat.category != facts.category and _contains(generated, cat.display_name) and not _contains(locked, cat.display_name):
                report.hard.append(f"mentions another category ({cat.display_name}); the category comes from Phase 3")

        extra_numbers = numbers_in(generated) - numbers_in(locked)
        if extra_numbers:
            (report.citizen_added if edit else report.soft).append(f"numbers not in the confirmed facts: {sorted(extra_numbers)}")
        for pattern, label in ((_EMAIL, "an email address"), (_PHONE, "a phone number")):
            for match in pattern.findall(body + " " + " ".join(values.values())):
                if normalise(match) not in citizen:
                    (report.citizen_added if edit else report.soft).append(f"contains {label} not given by the citizen")

        allowed = self._allowed_words(facts)
        new_words = sorted({w for w in _words(" ".join(values.values())) if _stem(w) not in allowed})
        if new_words:
            shown = ", ".join(new_words[:15]) + (" …" if len(new_words) > 15 else "")
            if edit:
                report.citizen_added.append(f"new wording not in the confirmed complaint: {shown}")
            else:
                report.soft.append(f"unsupported wording (not in the citizen's facts or the configured templates): {shown}")
        return report

    def missing_facts(self, sections: DraftSections, facts: DraftFactSet) -> list[str]:
        """Facts a rewritten (AI) draft must still carry."""
        text = normalise(" ".join(sections.model_dump().values()))
        missing: list[str] = []
        places = [facts.location.citizen_words, facts.location.value, facts.resolved_place or ""]
        if not any(p and normalise(p) in text for p in places):
            missing.append("the confirmed location")
        if facts.duration and not any(normalise(d) in text for d in (facts.duration.value, facts.duration.citizen_words)):
            missing.append("the confirmed duration")
        return missing
