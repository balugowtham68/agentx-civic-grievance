"""Deterministic draft builder: category template + locked facts -> administrative wording.

Templates hold wording only; every fact comes from the DraftFactSet. The duration
is inserted only if the citizen gave one. Citizen-provided location, the Phase 3
resolved place and the prototype jurisdiction are kept distinct in the text.
"""

from __future__ import annotations

from app.agents.drafting.config import DraftingConfig
from app.core.errors import AppError
from app.schemas.drafting import DraftFactSet, DraftSections, EvidenceReference
from app.services.intake.offline.text import is_latin, normalise

_LEADING_PREPOSITIONS = (
    "near", "on", "in", "at", "beside", "behind", "opposite", "outside", "next", "close", "between", "along",
    "by", "around", "inside", "from", "under", "over", "infront", "in front", "towards", "across",
)


# Fixed wording the builder itself adds around the facts (allowed vocabulary for the validator).
BUILDER_PHRASES = (
    "As described by the citizen", "area given by the citizen when asked", "Matched to",
    "in the prototype jurisdiction configuration", "Citizen's words", "clarified by the citizen",
    "Not stated by the citizen", "Approximately", "at the location described by the citizen as",
)


class DraftTemplateMissingError(AppError):
    status_code = 422
    code = "draft_template_missing"


def _sentence(text: str) -> str:
    text = " ".join(text.split())
    return text[:1].upper() + text[1:] if text else text


def _location_phrase(facts: DraftFactSet, config: DraftingConfig) -> str:
    value = facts.location.value.strip()
    if facts.citizen_language == "en" and is_latin(normalise(value)):
        lowered = value.lower()
        if not lowered.startswith(tuple(p + " " for p in _LEADING_PREPOSITIONS)):
            value = f"at {value}"
        return config.location_phrase["citizen_english"].format(location=value)
    return config.location_phrase["citizen_other_language"].format(location=facts.location.citizen_words)


def build_sections(facts: DraftFactSet, config: DraftingConfig) -> DraftSections:
    template = config.templates.get(facts.category)
    if template is None:
        raise DraftTemplateMissingError(f"No drafting template is configured for category {facts.category!r}")
    issue_value = facts.issue.value
    duration = config.duration_phrase.format(duration=facts.duration.value) if facts.duration else ""
    location = _location_phrase(facts, config)

    location_parts = [f"As described by the citizen: “{facts.location.citizen_words}”"]
    for answer in facts.location_answers:
        location_parts.append(f"area given by the citizen when asked: “{answer.citizen_words}”")
    location_text = "; ".join(location_parts) + "."
    if facts.jurisdiction_id:
        location_text += (
            f" Matched to {facts.resolved_place}, {facts.jurisdiction_name} ({facts.jurisdiction_id}) "
            "in the prototype jurisdiction configuration."
        )
    return DraftSections(
        subject=template.pick(template.subject, issue_value),
        summary=_sentence(template.pick(template.summary, issue_value).format(location=location, duration=duration)),
        issue_text=(
            f"{template.pick(template.issue_label, issue_value)}. Citizen's words: “{facts.issue.citizen_words}”"
            + "".join(f"; clarified by the citizen: “{a.citizen_words}”" for a in facts.category_answers)
            + "."
        ),
        location_text=location_text,
        duration_text=(
            f"Approximately {facts.duration.value} (citizen's words: “{facts.duration.citizen_words}”)."
            if facts.duration else "Not stated by the citizen."
        ),
        requested_action=template.requested_action,
    )


def compose_body(sections: DraftSections, facts: DraftFactSet, *, include_statement: bool, language_name: str) -> str:
    lines = [
        f"Subject: {sections.subject}",
        "",
        sections.summary,
        "",
        f"Issue: {sections.issue_text}",
        f"Location: {sections.location_text}",
        f"Duration: {sections.duration_text}",
    ]
    if facts.identifiers:
        lines.append("Identifiers given by the citizen: " + "; ".join(f"“{i.citizen_words}”" for i in facts.identifiers))
    lines += [
        "",
        f"Requested action: {sections.requested_action}",
        "",
        f"Category: {facts.category_name}",
        f"Responsible department (prototype configuration): {facts.department_name}",
        f"Jurisdiction (prototype configuration): {facts.jurisdiction_name or 'Not resolved'}",
    ]
    if include_statement:
        lines += ["", f"Citizen's statement (verbatim, {language_name}): “{facts.original_text}”"]
    return "\n".join(lines)


def supporting_facts(facts: DraftFactSet) -> list[str]:
    items = [f"Issue in the citizen's words: “{facts.issue.citizen_words}”",
             f"Location in the citizen's words: “{facts.location.citizen_words}”"]
    items += [f"Area given by the citizen when asked: “{a.citizen_words}”" for a in facts.location_answers]
    items += [f"Problem type chosen by the citizen when asked: “{a.citizen_words}”" for a in facts.category_answers]
    if facts.duration:
        items.append(f"Duration in the citizen's words: “{facts.duration.citizen_words}”")
    items += [f"Identifier in the citizen's words: “{i.citizen_words}”" for i in facts.identifiers]
    return items


def chronology(facts: DraftFactSet) -> list[str]:
    """Only what the citizen said about time; no dates are ever inferred."""
    if facts.duration is None:
        return []
    return [f"The citizen reports the issue has lasted approximately {facts.duration.value}."]


def evidence_references(facts: DraftFactSet) -> list[EvidenceReference]:
    refs = [
        EvidenceReference(kind="citizen", field="issue", text=facts.issue.citizen_words, source=facts.issue.source),
        EvidenceReference(kind="citizen", field="location", text=facts.location.citizen_words, source=facts.location.source),
    ]
    refs += [EvidenceReference(kind="citizen", field="location", text=a.citizen_words, source=a.source) for a in facts.location_answers]
    refs += [EvidenceReference(kind="citizen", field="issue", text=a.citizen_words, source=a.source) for a in facts.category_answers]
    if facts.duration:
        refs.append(EvidenceReference(kind="citizen", field="duration", text=facts.duration.citizen_words, source=facts.duration.source))
    refs += [
        EvidenceReference(kind="classification", field="category", text=facts.category_name, source=facts.category_record_id),
        EvidenceReference(kind="classification", field="department", text=facts.department_name, source=facts.department_id),
    ]
    if facts.jurisdiction_id:
        refs.append(EvidenceReference(
            kind="classification", field="jurisdiction", text=f"{facts.jurisdiction_name}: {facts.resolved_place}",
            source=facts.jurisdiction_id,
        ))
    locked = {facts.category_record_id, facts.department_id, facts.jurisdiction_id}
    refs += [
        EvidenceReference(kind="knowledge", field="reference", text="Knowledge-base record used by the classification", source=s)
        for s in facts.source_ids if s not in locked
    ]
    return refs
