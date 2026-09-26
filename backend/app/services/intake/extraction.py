"""Fact extraction contracts and the English pattern rules.

Every extractor only *proposes* facts (value + evidence + how it was found). The
Intake Agent then verifies each proposal against the citizen's own words and
discards anything whose evidence is not there (app/agents/intake/verification.py).

- OfflineIntakeEngine (offline/engine.py): the default, for all six languages.
- RuleBasedFactExtractor (here): English preposition/duration patterns used by the
  offline engine for English ("for three days", "near the main gate").
- AIFactExtractor: OPTIONAL Gemini layer through AIProvider, used only when the
  offline engine could not find a required fact. Never bypasses verification.
"""

from __future__ import annotations

import re
from typing import Literal, Protocol

from pydantic import BaseModel, Field

from app.prompts.intake import AIExtractionOutput, extraction_prompt
from app.services.ai import AIProvider

FactMethod = Literal["rule", "lexicon", "ai", "citizen"]
FactQuality = Literal["clear", "vague", "partial"]


class ProposedFact(BaseModel):
    value: str
    evidence: str
    statement_index: int = 0
    method: FactMethod = "rule"
    quality: FactQuality = "clear"


class ProposedEntity(ProposedFact):
    type: str


class ProposedFacts(BaseModel):
    issue: ProposedFact | None = None
    location: ProposedFact | None = None
    duration: ProposedFact | None = None
    entities: list[ProposedEntity] = Field(default_factory=list)


class FactExtractor(Protocol):
    name: str

    @property
    def available(self) -> bool: ...

    async def extract(self, statements: list[str], *, language: str) -> ProposedFacts: ...


class AIFactExtractor:
    def __init__(self, ai: AIProvider) -> None:
        self._ai = ai
        self.name = f"{ai.name}:{ai.model}"

    @property
    def available(self) -> bool:
        return self._ai.available

    async def extract(self, statements: list[str], *, language: str) -> ProposedFacts:
        output = await self._ai.generate_structured(extraction_prompt(statements, language), AIExtractionOutput)

        def fact(f: object) -> ProposedFact | None:
            if f is None:
                return None
            return ProposedFact(value=f.value, evidence=f.evidence, statement_index=f.statement_index, method="ai")  # type: ignore[attr-defined]

        return ProposedFacts(
            issue=fact(output.issue),
            location=fact(output.location),
            duration=fact(output.duration),
            entities=[
                ProposedEntity(type=e.type, value=e.value, evidence=e.evidence, statement_index=e.statement_index, method="ai")
                for e in output.entities
            ],
        )


# ---------------------------------------------------------------- rule-based fallback

_NUM = r"(?:\d+|a|an|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|few|several|couple\s+of)"
_UNIT = r"(?:hours?|days?|nights?|weeks?|months?|years?)"
_DURATION_PATTERNS: list[tuple[re.Pattern[str], bool]] = [
    # (pattern, value_is_whole_match)
    (re.compile(rf"\b(?:for|since|from)\s+(?:the\s+)?(?:(?:last|past)\s+)?(?:about\s+|almost\s+|over\s+|nearly\s+)?(?P<value>{_NUM}\s+{_UNIT})\b", re.I), False),
    (re.compile(rf"\b(?P<value>{_NUM}\s+{_UNIT})\s+(?:now|already|ago)\b", re.I), False),
    (re.compile(r"\bsince\s+(?P<value>yesterday|last\s+(?:night|week|month|year)|(?:mon|tues|wednes|thurs|fri|satur|sun)day)\b", re.I), True),
    # Bare "5 days" (e.g. a correction: "No, it is 5 days").
    (re.compile(rf"\b(?P<value>{_NUM}\s+{_UNIT})\b", re.I), False),
]

_STRONG_PREPOSITIONS = r"near(?:\s+to)?|in\s+front\s+of|opposite(?:\s+to)?|beside|behind|next\s+to|close\s+to|outside|adjacent\s+to"
_WEAK_PREPOSITIONS = r"at|on|in"
_LOCATION_RE = re.compile(
    rf"\b(?P<prep>{_STRONG_PREPOSITIONS}|{_WEAK_PREPOSITIONS})\s+(?P<place>[^.,;!?\n]+?)"
    r"(?=\s+(?:for|since|from|and|but|which|that|is|are|was|were|has|have|had|not)\b|[.,;!?\n]|$)",
    re.I,
)
# Words that follow at/on/in but are times or manners, not places.
_NOT_PLACES = {
    "night", "nights", "morning", "evening", "afternoon", "noon", "daytime", "time", "times",
    "all", "least", "last", "first", "once", "the", "a", "an", "and", "off", "and off",
    "this", "that", "it", "my", "our", "some", "many", "few", "months", "weeks", "days",
}

_PROBLEM_CUES = re.compile(
    r"\b(?:not|no|never|broken|damaged|leak\w*|overflow\w*|block\w*|garbage|waste|pothole\w*|dark|"
    r"stray|flood\w*|dirty|smell\w*|stink\w*|missing|fallen|collaps\w*|burst|stuck|problem|issue|"
    r"without|cracked|open|dump\w*|clog\w*)\b",
    re.I,
)

_IDENTIFIER_RE = re.compile(
    r"\b(?P<kind>pole|house|door|plot|flat|meter|ward|shop)\s*(?:no\.?|number|num|#)\s*[:.]?\s*(?P<id>[A-Za-z]?\d[\w/-]*)",
    re.I,
)
_PLACE_NOUNS = (
    r"hostel|school|temple|hospital|market|road|street|nagar|colony|college|park|station|"
    r"church|mosque|gate|junction|circle|layout|bank|apartments?|complex|office|stadium|lake|bridge"
)
_LANDMARK_RE = re.compile(
    rf"\b(?P<name>(?:[A-Z][\w&'.-]*\s+){{0,3}}(?:[A-Z]{{2,}}|[A-Z][a-z]+)\s+(?i:{_PLACE_NOUNS}))\b"
)
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+|\n+")


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip(" ,;:-")


class RuleBasedFactExtractor:
    """Deterministic English-only fallback. Conservative by design."""

    name = "english_patterns"

    @property
    def available(self) -> bool:
        return True

    def _duration(self, text: str) -> ProposedFact | None:
        for pattern, whole in _DURATION_PATTERNS:
            match = pattern.search(text)
            if match:
                value = match.group(0) if whole else match.group("value")
                return ProposedFact(value=_clean(value), evidence=_clean(match.group(0)))
        return None

    def _location(self, text: str) -> ProposedFact | None:
        candidates = []
        for match in _LOCATION_RE.finditer(text):
            place = _clean(match.group("place"))
            first = place.lower().split(" ")[0] if place else ""
            if not place or place.lower() in _NOT_PLACES or first in _NOT_PLACES - {"the", "a", "an", "my", "our", "this", "that"}:
                continue
            if len(place.split()) > 12 or not re.search(r"[A-Za-z]", place):
                continue
            # A trailing duration phrase is not part of the place.
            if re.match(rf"^{_NUM}\s+{_UNIT}$", place, re.I):
                continue
            strong = re.fullmatch(_STRONG_PREPOSITIONS, match.group("prep"), re.I) is not None
            candidates.append((0 if strong else 1, match.start(), match))
        if not candidates:
            return None
        _, _, best = sorted(candidates, key=lambda c: (c[0], c[1]))[0]
        span = _clean(best.group(0))
        return ProposedFact(value=span, evidence=span)

    def _issue(self, text: str, remove: list[str]) -> ProposedFact | None:
        sentence = _SENTENCE_END.split(text.strip())[0]
        if not _PROBLEM_CUES.search(sentence):
            return None
        value = sentence
        for span in remove:
            value = re.sub(re.escape(span), " ", value, flags=re.I)
        value = _clean(re.sub(r"[.!?]+$", "", value))
        value = re.sub(r"^(?:the|a|an|my|our)\s+", "", value, flags=re.I)
        value = re.sub(r"\s+(?:now|already)$", "", value, flags=re.I)
        if len(value.split()) < 2:
            return None
        return ProposedFact(value=value[0].upper() + value[1:], evidence=_clean(re.sub(r"[.!?]+$", "", sentence)))

    def _entities(self, text: str) -> list[ProposedEntity]:
        entities: list[ProposedEntity] = []
        seen: set[str] = set()
        for match in _IDENTIFIER_RE.finditer(text):
            value = f"{match.group('kind').lower()} number {match.group('id')}"
            if value not in seen:
                seen.add(value)
                entities.append(ProposedEntity(type="identifier", value=value, evidence=_clean(match.group(0))))
        for match in _LANDMARK_RE.finditer(text):
            name = _clean(match.group("name"))
            words = name.split()
            # A capitalised first word of a sentence is not evidence of a proper name.
            if match.start() == 0 and len(words) == 2 and not words[0].isupper():
                continue
            if name.lower() not in seen and not name.lower().startswith(("the ", "street light", "streetlight")):
                seen.add(name.lower())
                entities.append(ProposedEntity(type="landmark", value=name, evidence=name))
        return entities

    def extract_one(self, statement: str, index: int = 0) -> ProposedFacts:
        duration = self._duration(statement)
        location = self._location(statement)
        remove = [f.evidence for f in (duration, location) if f is not None]
        facts = ProposedFacts(duration=duration, location=location, issue=self._issue(statement, remove))
        facts.entities = self._entities(statement)
        for fact in (facts.issue, facts.location, facts.duration, *facts.entities):
            if fact is not None:
                fact.statement_index = index
        return facts

    async def extract(self, statements: list[str], *, language: str) -> ProposedFacts:
        result = ProposedFacts()
        for index, statement in enumerate(statements):
            found = self.extract_one(statement, index)
            for field in ("issue", "location", "duration"):
                if getattr(result, field) is None:
                    setattr(result, field, getattr(found, field))
            result.entities += found.entities
        return result
