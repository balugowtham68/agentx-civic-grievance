"""Offline Intake Engine: deterministic, multilingual fact extraction.

Runs with no network and no API key, for every configured language that has a
resource file. Layers (lowest cost first):

1. Pattern rules    - English prepositions/durations (RuleBasedFactExtractor),
                      digits + units, identifier markers ("pole no. 14").
2. Language lexicon - backend/resources/intake/<lang>.json: issue subjects +
                      problem phrases, number words + duration units, place
                      nouns + possessives + postpositions, romanised variants.

How facts are found:
- issue    = a configured subject ("street light", "தெரு விளக்கு") paired with a
             nearby problem phrase ("not working", "எரியல"). A subject with no
             problem phrase gives a PARTIAL issue ("problem with the street light").
- duration = number word/digit directly followed by a time unit ("மூணு நாளா").
- location = a run of tokens around a place noun or postposition
             ("எங்க தெருவுல" -> "our street", "రామాలయం దగ్గర" -> "near రామాలయం").
             Unknown words in a location are kept in the citizen's script, never
             transliterated or guessed. Generic places ("our street") are VAGUE.

Everything returned is a proposal with exact evidence; the agent still verifies it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.services.intake.extraction import (
    ProposedEntity,
    ProposedFact,
    ProposedFacts,
    RuleBasedFactExtractor,
)
from app.services.intake.offline.resources import IntakeResources, SafetyResources
from app.services.intake.offline.text import NormalisedText, PhraseMatcher, Span, normalise

NUMBER_WORDS_EN = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven",
                   8: "eight", 9: "nine", 10: "ten", 11: "eleven", 12: "twelve"}
_DIGITS = re.compile(r"\d{1,3}")
MAX_ISSUE_GAP_TOKENS = 8
MAX_UNKNOWN_LOCATION_TOKENS = 2


def english_duration(amount: int, unit: str) -> str:
    number = NUMBER_WORDS_EN.get(amount, str(amount))
    return f"{number} {unit}{'' if amount == 1 else 's'}"


@dataclass
class _Roles:
    """Role of each token in a statement, for building location runs."""

    roles: list[str]
    glosses: list[str | None]


class LanguageEngine:
    def __init__(self, resources: IntakeResources) -> None:
        r = resources
        self.resources = r
        entries = lambda items: [(p, e.value) for e in items for p in e.patterns]  # noqa: E731
        self.subjects = PhraseMatcher(entries(r.issue_subjects), "subject", "prefix")
        self.states = PhraseMatcher(entries(r.problem_states), "state", "prefix")
        self.places = PhraseMatcher(entries(r.place_nouns), "place", "prefix")
        self.possessives = PhraseMatcher(entries(r.possessives), "possessive", "word")
        self.proximity = PhraseMatcher(entries(r.proximity), "proximity", "word")
        self.particles = PhraseMatcher([(p, "") for p in r.particles], "particle", "word")
        self.numbers = PhraseMatcher([(w, str(n)) for w, n in r.number_words.items()], "number", "word")
        self.units = PhraseMatcher([(p, u.unit) for u in r.duration_units for p in u.patterns], "unit", "prefix")
        self.duration_particles = PhraseMatcher([(p, "") for p in r.duration_particles], "dparticle", "word")
        self.stopwords = {normalise(w) for w in r.latin_markers + r.correction_phrases + r.confirmation_phrases}
        markers = "|".join(re.escape(normalise(m)) for m in sorted(r.identifier_markers, key=len, reverse=True))
        self.identifier_re = (
            re.compile(rf"(?<!\w)(?P<marker>{markers})\s*[.:#]?\s*(?P<id>[a-z]?\d[\w/-]*)") if markers else None
        )

    # ---------------------------------------------------------------- pieces

    def issue(self, text: NormalisedText, subjects: list[Span], states: list[Span]) -> ProposedFact | None:
        def token_gap(a: Span, b: Span) -> int:
            first, second = (a, b) if a.start <= b.start else (b, a)
            return sum(1 for t in text.tokens if first.end <= t.start and t.end <= second.start)

        best: tuple[int, Span, Span] | None = None
        for subject in subjects:
            for state in states:
                if state.start < subject.end and subject.start < state.end:
                    continue
                gap = token_gap(subject, state)
                if gap <= MAX_ISSUE_GAP_TOKENS:
                    rank = gap + (0 if state.start >= subject.end else 1)  # prefer subject before state
                    if best is None or rank < best[0]:
                        best = (rank, subject, state)
        if best is not None:
            _, subject, state = best
            start, end = min(subject.start, state.start), max(subject.end, state.end)
            return ProposedFact(
                value=f"{subject.value} {state.value}",
                evidence=text.original_slice(start, end),
                method="lexicon",
            )
        if subjects:
            subject = subjects[0]
            return ProposedFact(
                value=f"problem with the {subject.value}",
                evidence=text.original_slice(subject.start, subject.end),
                method="lexicon",
                quality="partial",
            )
        return None

    def duration(self, text: NormalisedText) -> ProposedFact | None:
        numbers = [(s.start, s.end, int(s.value)) for s in self.numbers.find(text)]
        numbers += [(m.start(), m.end(), int(m.group(0))) for m in _DIGITS.finditer(text.norm)]
        units = self.units.find(text)
        particles = self.duration_particles.find(text)
        for start, end, amount in sorted(numbers):
            if amount <= 0:
                continue
            unit = next((u for u in units if u.start >= end and text.norm[end:u.start].strip() == ""), None)
            if unit is None:
                continue
            stop = unit.end
            particle = next((p for p in particles if p.start >= stop and text.norm[stop:p.start].strip() == ""), None)
            if particle is not None:
                stop = particle.end
            return ProposedFact(
                value=english_duration(amount, unit.value),
                evidence=text.original_slice(start, stop),
                method="lexicon",
            )
        return None

    def _roles(self, text: NormalisedText, blocked: list[Span]) -> _Roles:
        roles = ["other"] * len(text.tokens)
        glosses: list[str | None] = [None] * len(text.tokens)

        def mark(spans: list[Span], role: str) -> None:
            for span in spans:
                for i, tok in enumerate(text.tokens):
                    if span.start < tok.end and tok.start < span.end and roles[i] == "other":
                        roles[i] = role
                        glosses[i] = span.value

        mark(blocked, "issue")
        mark(self.numbers.find(text), "duration")
        mark(self.units.find(text), "duration")
        mark(self.duration_particles.find(text), "duration")
        mark([s for s in self.proximity.find(text)], "proximity")
        mark(self.possessives.find(text), "possessive")
        mark(self.places.find(text), "place")
        mark(self.particles.find(text), "particle")
        for i, tok in enumerate(text.tokens):
            if roles[i] == "other" and (tok.text in self.stopwords or _DIGITS.fullmatch(tok.text)):
                roles[i] = "stop"
        return _Roles(roles, glosses)

    def location(self, text: NormalisedText, blocked: list[Span]) -> tuple[ProposedFact | None, list[str]]:
        """Postposition-style location runs. Returns the fact and unknown (name) words."""
        r = self._roles(text, blocked)
        best: tuple[int, int, int] | None = None  # (score, start_token, end_token)
        for anchor, role in enumerate(r.roles):
            if role not in {"place", "proximity"}:
                continue
            left = anchor
            unknown = 0
            while left - 1 >= 0 and r.roles[left - 1] in {"possessive", "place", "other"}:
                if r.roles[left - 1] == "other":
                    if unknown >= MAX_UNKNOWN_LOCATION_TOKENS:
                        break
                    unknown += 1
                left -= 1
            right = anchor
            while right + 1 < len(r.roles) and r.roles[right + 1] in {"proximity", "particle", "place"}:
                right += 1
            if role == "proximity" and left == anchor:
                continue  # a postposition with no object is not a location
            span_roles = r.roles[left : right + 1]
            score = 2 * span_roles.count("other") + span_roles.count("proximity") + span_roles.count("place")
            if best is None or score > best[0]:
                best = (score, left, right)
        if best is None:
            return None, []
        _, left, right = best
        tokens = text.tokens[left : right + 1]
        roles = r.roles[left : right + 1]
        glosses = r.glosses[left : right + 1]
        original_words = [text.original_slice(t.start, t.end) for t in tokens]
        unknown_words = [w for w, role in zip(original_words, roles) if role == "other"]
        # Consecutive unknown words form one name ("रामलीला मैदान").
        names: list[str] = []
        previous_other = False
        for word, role in zip(original_words, roles):
            if role == "other":
                if previous_other:
                    names[-1] = f"{names[-1]} {word}"
                else:
                    names.append(word)
            previous_other = role == "other"

        proximity = [g for g, role in zip(glosses, roles) if role == "proximity" and g]
        possessive = [g for g, role in zip(glosses, roles) if role == "possessive" and g]
        places = [g for g, role in zip(glosses, roles) if role == "place" and g]
        parts = proximity[:1] + possessive[:1] + unknown_words + places[-1:]
        if possessive and not places and not unknown_words:
            return None, []  # "our" alone is not a place
        value = " ".join(p for p in parts if p)
        generic = set(self.resources.generic_places)
        vague = not unknown_words and all(p in generic for p in places)
        # Trim trailing particles from evidence ("हमारी गली की" -> keep; it is the citizen's words).
        evidence = text.original_slice(tokens[0].start, tokens[-1].end)
        return (
            ProposedFact(value=value, evidence=evidence, method="lexicon", quality="vague" if vague else "clear"),
            names,
        )

    def identifiers(self, text: NormalisedText) -> list[ProposedEntity]:
        if self.identifier_re is None:
            return []
        found = []
        for match in self.identifier_re.finditer(text.norm):
            evidence = text.original_slice(match.start(), match.end())
            found.append(
                ProposedEntity(type="identifier", value=f"number {match.group('id').upper()}", evidence=evidence, method="lexicon")
            )
        return found

    # ---------------------------------------------------------------- statement

    def extract_statement(
        self,
        statement: str,
        index: int,
        *,
        allow_partial_issue: bool = True,
        place_phrases: list[str] | None = None,
    ) -> ProposedFacts:
        """`place_phrases`: phrases already known to be the location (English rules);
        a subject word inside them names a place ("Main Road"), not the problem."""
        text = NormalisedText(statement)
        subjects, states = self.subjects.find(text), self.states.find(text)
        for phrase in place_phrases or []:
            needle = normalise(phrase)
            at = text.norm.find(needle) if needle else -1
            if at >= 0:
                subjects = [s for s in subjects if not (s.start >= at and s.end <= at + len(needle))]
        issue = self.issue(text, subjects, states)
        if issue is not None and issue.quality == "partial" and not allow_partial_issue:
            issue = None
        location, names = self.location(text, subjects + states)
        facts = ProposedFacts(issue=issue, location=location, duration=self.duration(text))
        facts.entities = self.identifiers(text)
        if location is not None:
            for name in names:
                facts.entities.append(ProposedEntity(type="place", value=name, evidence=name, method="lexicon"))
        for fact in (facts.issue, facts.location, facts.duration, *facts.entities):
            if fact is not None:
                fact.statement_index = index
        return facts


class OfflineIntakeEngine:
    """Deterministic multilingual extraction. No network, no API key, no model."""

    name = "offline_rules"

    def __init__(self, resources: dict[str, IntakeResources], safety: SafetyResources | None = None) -> None:
        self.languages = {code: LanguageEngine(r) for code, r in resources.items()}
        self._english_rules = RuleBasedFactExtractor()
        self._safety = [normalise(p) for p in (safety.instruction_like_phrases if safety else [])]

    @property
    def available(self) -> bool:
        return True

    def supports(self, language: str) -> bool:
        return language in self.languages

    def resources(self, language: str) -> IntakeResources | None:
        engine = self.languages.get(language)
        return engine.resources if engine else None

    def safety_flags(self, text: str) -> list[str]:
        norm = normalise(text)
        return ["instruction_like_text"] if any(p in norm for p in self._safety) else []

    async def extract(self, statements: list[str], *, language: str) -> ProposedFacts:
        return self.extract_sync(statements, language=language)

    def extract_sync(self, statements: list[str], *, language: str, corrections_mode: bool = False) -> ProposedFacts:
        engine = self.languages.get(language)
        if engine is None:
            raise LookupError(f"No offline intake resources for language {language!r}")
        result = ProposedFacts()
        for index, statement in enumerate(statements):
            places: list[str] = []
            if language == "en":
                rule_location = self._english_rules.extract_one(statement, index).location
                places = [rule_location.evidence] if rule_location is not None else []
            found = engine.extract_statement(
                statement, index, allow_partial_issue=not corrections_mode, place_phrases=places
            )
            if language == "en":
                found = self._merge_english(found, statement, index, corrections_mode)
            if (
                found.issue is not None
                and found.issue.quality != "clear"
                and found.location is not None
                and normalise(found.issue.evidence) in normalise(found.location.evidence)
            ):
                # "Gandhi Road" names a place; a bare subject inside the location is not a problem report.
                found.issue = None
            for field in ("issue", "location", "duration"):
                current, new = getattr(result, field), getattr(found, field)
                # Keep the first fact, but a clear fact replaces a partial/vague one.
                if new is not None and (current is None or (current.quality != "clear" and new.quality == "clear")):
                    setattr(result, field, new)
            seen = {(e.type, e.value.lower()) for e in result.entities}
            result.entities += [e for e in found.entities if (e.type, e.value.lower()) not in seen]
        return result

    def _merge_english(self, found: ProposedFacts, statement: str, index: int, corrections_mode: bool) -> ProposedFacts:
        """English: prepositional/duration patterns fill what the lexicon did not."""
        rules = self._english_rules.extract_one(statement, index)
        if rules.location is not None:
            words = set(normalise(rules.location.value).split())
            filler = {"near", "to", "close", "beside", "next", "behind", "opposite", "in", "front", "of", "on", "at",
                      "outside", "the", "a", "an", "my", "our", "this", "that"}
            generic = set(self.languages["en"].resources.generic_places) | {"home"}
            vague = bool(words - filler) and (words - filler) <= generic
            found.location = ProposedFact(
                value=rules.location.value, evidence=rules.location.evidence, statement_index=index,
                method="rule", quality="vague" if vague else "clear",
            )
        if rules.duration is not None:  # English patterns keep "for"/"since" in the evidence
            found.duration = rules.duration.model_copy(update={"statement_index": index, "method": "rule"})
        if found.issue is None and rules.issue is not None and not corrections_mode:
            found.issue = rules.issue.model_copy(update={"statement_index": index, "method": "rule"})
        seen = {(e.type, e.value.lower()) for e in found.entities}
        for entity in rules.entities:
            if (entity.type, entity.value.lower()) not in seen and not (
                entity.type == "identifier" and any(e.type == "identifier" for e in found.entities)
            ):
                found.entities.append(entity.model_copy(update={"statement_index": index, "method": "rule"}))
        return found

    def parse_correction(self, text: str, *, language: str) -> ProposedFacts:
        """Facts stated in a free-text correction ("No, it is 5 days"). Leading
        yes/no words are ignored; only fields actually found are returned."""
        engine = self.languages.get(language) or self.languages["en"]
        phrases = sorted(
            (normalise(p) for p in engine.resources.correction_phrases + engine.resources.confirmation_phrases),
            key=len,
            reverse=True,
        )
        stripped = text.strip()
        changed = True
        while changed:
            changed = False
            lowered = normalise(stripped)
            for phrase in phrases:
                if lowered.startswith(phrase) and (len(lowered) == len(phrase) or not lowered[len(phrase)].isalnum()):
                    stripped = stripped[len(phrase):].lstrip(" ,.:;-!")
                    changed = True
                    break
        if not stripped:
            return ProposedFacts()
        return self.extract_sync([stripped], language=language if language in self.languages else "en", corrections_mode=True)
