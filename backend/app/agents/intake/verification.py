"""Evidence validator - the no-hallucination guard. Applies to EVERY layer
(offline rules, lexicons and the optional AI provider alike).

A proposed fact is accepted only if its evidence is found in the citizen's own
statements (after the same normalisation the offline engine uses: case, spacing,
zero-width joiners, Malayalam chillu forms, curly quotes). Rejected proposals are
kept for the audit trail and are never shown as facts.
"""

from __future__ import annotations

import re
from functools import lru_cache

from app.schemas.intake import (
    MAX_FACT_CHARS,
    ExtractedEntity,
    ExtractedField,
    ExtractedGrievance,
    IntakeField,
    RejectedFact,
)
from app.services.intake.extraction import ProposedFact, ProposedFacts
from app.services.intake.offline.text import normalise as _normalise

ALLOWED_ENTITY_TYPES = {"landmark", "place", "identifier", "organisation", "other"}
MAX_ENTITIES = 10
_DIGITS = re.compile(r"\d+")
_EDGE_PUNCTUATION = " .,;:!?\"'"


def normalise(text: str) -> str:
    return _normalise(text).strip(_EDGE_PUNCTUATION)


def locate_evidence(evidence: str, statements: list[str], hint: int = 0) -> int | None:
    """Index of the citizen statement that contains `evidence`, or None."""
    needle = normalise(evidence)
    if not needle:
        return None
    order = (
        [hint] + [i for i in range(len(statements)) if i != hint]
        if 0 <= hint < len(statements)
        else list(range(len(statements)))
    )
    for index in order:
        if needle in normalise(statements[index]):
            return index
    return None


@lru_cache(maxsize=1)
def _number_words() -> dict[str, int]:
    """Number words from every language resource ("three", "மூன்று", "तीन" -> 3).
    Articles such as "a"/"an" are ignored so they never count as numbers."""
    from app.services.intake.offline.resources import load_resources

    words: dict[str, int] = {}
    for resources in load_resources().values():
        for word, number in resources.number_words.items():
            key = _normalise(word)
            if len(key) > 2:
                words[key] = number
    return words


def _numbers(text: str) -> set[int]:
    norm = _normalise(text)
    found = {int(d) for d in _DIGITS.findall(norm)}
    words = _number_words()
    for word, number in words.items():
        # Latin words need a full word match ("ten" is not in "tenant"); Indic words take suffixes.
        tail = r"(?!\w)" if word.isascii() else ""
        if re.search(rf"(?<!\w){re.escape(word)}{tail}", norm):
            found.add(number)
    return found


def numbers_in(text: str) -> set[int]:
    """Numbers stated in text, as digits or number words in any supported language."""
    return _numbers(text)


def _numbers_consistent(value: str, evidence: str) -> bool:
    """If the citizen stated numbers (digits or number words), the value may not introduce different ones."""
    evidence_numbers = _numbers(evidence)
    return not evidence_numbers or _numbers(value) <= evidence_numbers


def _check(fact: ProposedFact, statements: list[str]) -> tuple[int | None, str | None]:
    value, evidence = fact.value.strip(), fact.evidence.strip()
    if not value or not evidence:
        return None, "empty value or evidence"
    if len(value) > MAX_FACT_CHARS:
        return None, "value too long"
    index = locate_evidence(evidence, statements, fact.statement_index)
    if index is None:
        return None, "evidence not found in the citizen's words"
    if not _numbers_consistent(value, evidence):
        return None, "value contains numbers the citizen did not state"
    return index, None


def verify_facts(proposed: ProposedFacts, statements: list[str]) -> tuple[ExtractedGrievance, list[RejectedFact]]:
    accepted = ExtractedGrievance()
    rejected: list[RejectedFact] = []

    for field in IntakeField:
        fact: ProposedFact | None = getattr(proposed, field.value)
        if fact is None:
            continue
        index, reason = _check(fact, statements)
        if reason is not None:
            rejected.append(RejectedFact(field=field.value, value=fact.value, claimed_evidence=fact.evidence, reason=reason))
            continue
        setattr(
            accepted,
            field.value,
            ExtractedField(
                value=fact.value.strip(),
                source_span=fact.evidence.strip(),
                statement_index=index,
                method=fact.method,
                quality=fact.quality,
            ),
        )

    seen: set[tuple[str, str]] = set()
    for entity in proposed.entities[: MAX_ENTITIES * 2]:
        index, reason = _check(entity, statements)
        if reason is not None:
            rejected.append(
                RejectedFact(field=f"entity:{entity.type}", value=entity.value, claimed_evidence=entity.evidence, reason=reason)
            )
            continue
        entity_type = entity.type.strip().lower()
        entity_type = entity_type if entity_type in ALLOWED_ENTITY_TYPES else "other"
        key = (entity_type, normalise(entity.value))
        if key in seen or len(accepted.entities) >= MAX_ENTITIES:
            continue
        seen.add(key)
        accepted.entities.append(
            ExtractedEntity(
                type=entity_type,
                value=entity.value.strip(),
                source_span=entity.evidence.strip(),
                statement_index=index,
                method=entity.method,
                quality=entity.quality,
            )
        )
    return accepted, rejected
