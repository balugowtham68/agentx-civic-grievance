"""Deterministic rule validation for classification - driven entirely by configuration.

Every rule here comes from knowledge_base/ (category issue patterns, ambiguity
groups, jurisdiction places and aliases, vague-location phrases) or from the
Phase 2 language resources (proximity words). There is no category-specific
if/else logic in code: adding a category or a phrase is a configuration change.

Matching reuses the Phase 2 multilingual text tools (normalisation with a map
back to the original, script-aware phrase boundaries), so every match reports
the citizen's exact words.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.schemas.classification import RuleMatch
from app.schemas.reference import AmbiguityGroup, CivicCategory, Jurisdiction, ReferenceData
from app.services.intake.offline.resources import load_resources
from app.services.intake.offline.text import NormalisedText, PhraseMatcher, normalise

_DIGIT = re.compile(r"\d")


@dataclass(frozen=True)
class CitizenText:
    """A piece of the citizen's own words and where it came from."""

    source: str  # original_text | issue | location | answer | correction
    text: str


@dataclass(frozen=True)
class PlaceMatch:
    jurisdiction: Jurisdiction
    place: str
    kind: str  # locality | landmark
    words: str
    source: str


class CivicRuleSet:
    """Compiled matchers for one loaded knowledge base."""

    def __init__(self, data: ReferenceData) -> None:
        self.data = data
        self._categories: dict[str, tuple[CivicCategory, PhraseMatcher, dict[str, str]]] = {}
        for cat in data.active_categories():
            phrases = cat.phrases()
            languages = {normalise(p): lang for lang, p in phrases}
            matcher = PhraseMatcher([(p, p) for _, p in phrases], f"cat:{cat.category}", "prefix")
            self._categories[cat.category] = (cat, matcher, languages)
        self._groups: list[tuple[AmbiguityGroup, PhraseMatcher, dict[str, str]]] = []
        for group in data.ambiguity_groups:
            terms = [(lang, t) for lang, items in group.terms.items() for t in items]
            self._groups.append(
                (group, PhraseMatcher([(t, t) for _, t in terms], f"amb:{group.id}", "prefix"),
                 {normalise(t): lang for lang, t in terms})
            )
        self._places: list[tuple[Jurisdiction, str, str, PhraseMatcher]] = []
        for jur in data.jurisdictions:
            for name, kind, spellings in jur.places():
                self._places.append((jur, name, kind, PhraseMatcher([(s, name) for s in spellings], "place", "prefix")))
        settings = data.classification
        vague = [p for items in (settings.vague_location_phrases.values() if settings else []) for p in items]
        self._vague = PhraseMatcher([(p, p) for p in vague], "vague", "prefix")
        proximity = [p for res in load_resources().values() for entry in res.proximity for p in entry.patterns]
        self._proximity = PhraseMatcher([(p, p) for p in proximity], "proximity", "word")

    # ------------------------------------------------------------------ categories

    def category_matches(self, texts: list[CitizenText]) -> dict[str, list[RuleMatch]]:
        hits: dict[str, list[RuleMatch]] = {}
        for piece in texts:
            normalised = NormalisedText(piece.text)
            for key, (cat, matcher, languages) in self._categories.items():
                for span in matcher.find(normalised):
                    pattern = normalise(span.value)
                    hits.setdefault(key, []).append(
                        RuleMatch(
                            rule_id=cat.id,
                            rule_type="category_pattern",
                            category=key,
                            pattern=span.value,
                            language=languages.get(pattern, "en"),
                            citizen_words=normalised.original_slice(span.start, span.end),
                            source=piece.source,  # type: ignore[arg-type]
                        )
                    )
        return hits

    def suppressed(self, matched: set[str]) -> dict[str, str]:
        """category -> the more specific matched category that suppresses it (configured)."""
        result: dict[str, str] = {}
        for key in matched:
            cat = self._categories[key][0]
            for other in cat.suppresses:
                if other in matched and key not in self._categories[other][0].suppresses:
                    result[other] = key
        return result

    def ambiguity_matches(self, texts: list[CitizenText]) -> list[tuple[AmbiguityGroup, RuleMatch]]:
        found: list[tuple[AmbiguityGroup, RuleMatch]] = []
        for piece in texts:
            normalised = NormalisedText(piece.text)
            for group, matcher, languages in self._groups:
                for span in matcher.find(normalised):
                    found.append(
                        (group, RuleMatch(
                            rule_id=group.id, rule_type="ambiguity_term", pattern=span.value,
                            language=languages.get(normalise(span.value), "en"),
                            citizen_words=normalised.original_slice(span.start, span.end),
                            source=piece.source,  # type: ignore[arg-type]
                        ))
                    )
        return found

    def category(self, key: str) -> CivicCategory | None:
        entry = self._categories.get(key)
        return entry[0] if entry else None

    # ------------------------------------------------------------------ locations

    def place_matches(self, piece: CitizenText) -> list[PlaceMatch]:
        normalised = NormalisedText(piece.text)
        found: list[PlaceMatch] = []
        for jur, name, kind, matcher in self._places:
            for span in matcher.find(normalised):
                found.append(PlaceMatch(jur, name, kind, normalised.original_slice(span.start, span.end), piece.source))
        return found

    def is_vague(self, text: str) -> bool:
        return bool(self._vague.find(NormalisedText(text)))

    def has_proximity(self, text: str) -> bool:
        return bool(self._proximity.find(NormalisedText(text)))

    @staticmethod
    def has_number(text: str) -> bool:
        return bool(_DIGIT.search(text))


__all__ = ["CitizenText", "CivicRuleSet", "PlaceMatch"]
