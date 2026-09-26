"""Phase 2 missing-information policy and clarification questions.

Generic baseline (Phase 3 adds category-specific required fields through
IntakeResult.category_required_fields without changing this contract):

| Field    | Requirement           | Why                                               |
| -------- | --------------------- | ------------------------------------------------- |
| issue    | REQUIRED_TO_CONTINUE  | Nothing can be done without knowing what is wrong |
| location | REQUIRED_TO_CONTINUE  | Every civic complaint must be routed to a place   |
| duration | OPTIONAL              | Useful, but never asked for on its own            |

Questions are asked only for REQUIRED fields that are missing. Their text comes
from backend/resources/intake/<lang>.json (fixed templates, never generated), so a
question cannot introduce facts. Non-English templates are drafts pending review.
"""

from __future__ import annotations

from app.schemas.intake import (
    ClarificationQuestion,
    ExtractedGrievance,
    FieldRequirement,
    IntakeField,
    MissingField,
)
from app.services.intake.offline.resources import QuestionTemplates

FIELD_POLICY: dict[IntakeField, FieldRequirement] = {
    IntakeField.ISSUE: FieldRequirement.REQUIRED_TO_CONTINUE,
    IntakeField.LOCATION: FieldRequirement.REQUIRED_TO_CONTINUE,
    IntakeField.DURATION: FieldRequirement.OPTIONAL,
}

_REASONS: dict[IntakeField, str] = {
    IntakeField.ISSUE: "The problem was not described",
    IntakeField.LOCATION: "The place of the problem was not mentioned",
    IntakeField.DURATION: "How long the problem has lasted was not mentioned",
}


def missing_information(extracted: ExtractedGrievance, *, extraction_ran: bool) -> list[MissingField]:
    if not extraction_ran:
        return [
            MissingField(field=field, requirement=FieldRequirement.UNKNOWN, reason="Information could not be extracted yet")
            for field in IntakeField
        ]
    return [
        MissingField(field=field, requirement=requirement, reason=_REASONS[field])
        for field, requirement in FIELD_POLICY.items()
        if extracted.get(field) is None
    ]


def has_blocking_gap(missing: list[MissingField]) -> bool:
    return any(m.requirement is FieldRequirement.REQUIRED_TO_CONTINUE for m in missing)


def clarification_questions(
    missing: list[MissingField],
    *,
    templates: QuestionTemplates,
    language: str,
    issue: str | None = None,
) -> list[ClarificationQuestion]:
    questions: list[ClarificationQuestion] = []
    for item in missing:
        if item.requirement is not FieldRequirement.REQUIRED_TO_CONTINUE:
            continue
        if item.field is IntakeField.LOCATION and issue and templates.location_with_issue:
            text = templates.location_with_issue.format(issue=issue)
        else:
            text = getattr(templates, item.field.value)
        questions.append(ClarificationQuestion(field=item.field, text=text, language=language))
    return questions
