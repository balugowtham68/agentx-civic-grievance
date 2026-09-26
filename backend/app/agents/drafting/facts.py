"""Fact locking: build the DraftFactSet from the confirmed Phase 2 handoff and the
Phase 3 classification result. Nothing is re-classified here; Phase 3 output is
only checked for completeness and consistency with the knowledge base.
"""

from __future__ import annotations

from app.core.errors import AppError, ConflictError
from app.schemas.classification import (
    ClassificationResult,
    ClassificationStatus,
    JurisdictionStatus,
)
from app.schemas.drafting import DraftFactSet, LockedFact
from app.schemas.intake import IntakeHandoff
from app.schemas.reference import ReferenceData

_NOT_CLASSIFIED_REASON = {
    ClassificationStatus.NEEDS_INFO: "Draft unavailable. Reason: required classification/location information is incomplete.",
    ClassificationStatus.AMBIGUOUS: "Draft unavailable. Reason: the classification is ambiguous; the citizen must first choose the category.",
    ClassificationStatus.UNSUPPORTED_CLASSIFICATION: "Draft unavailable. Reason: the complaint could not be classified from the civic knowledge base.",
}


class NotClassifiedError(ConflictError):
    code = "complaint_not_classified"


class ClassificationIncompleteError(AppError):
    status_code = 422
    code = "classification_incomplete"


def build_fact_set(
    handoff: IntakeHandoff, classification: ClassificationResult, data: ReferenceData, *, safety_flags: list[str]
) -> DraftFactSet:
    if classification.classification_status is not ClassificationStatus.CLASSIFIED:
        raise NotClassifiedError(_NOT_CLASSIFIED_REASON[classification.classification_status])
    problems: list[str] = []
    category = data.category(classification.category or "")
    if category is None or category.id != classification.category_record_id:
        problems.append("the classified category is not an active knowledge-base category")
    department = classification.responsible_department
    dept = next((d for d in data.departments if department and d.id == department.department_id), None)
    if department is None or dept is None:
        problems.append("the responsible department is missing or not configured")
    elif category is not None and dept.id != category.department_id:
        problems.append("the department does not match the configured category mapping")
    jurisdiction = classification.jurisdiction
    if jurisdiction.jurisdiction_id and jurisdiction.jurisdiction_id not in {j.id for j in data.jurisdictions}:
        problems.append("the jurisdiction is not configured")
    if category is not None and category.jurisdiction_required and jurisdiction.status is not JurisdictionStatus.RESOLVED:
        problems.append("the jurisdiction required for this category is not resolved")
    if not handoff.issue.source_span.strip() or not handoff.location.source_span.strip():
        problems.append("citizen evidence for the issue or location is empty")
    if problems:
        raise ClassificationIncompleteError("Draft unavailable: " + "; ".join(problems))
    assert category is not None and dept is not None and department is not None

    sources = {e.source for e in classification.evidence if e.kind == "knowledge"}
    sources |= {category.id, dept.id} | ({jurisdiction.jurisdiction_id} if jurisdiction.jurisdiction_id else set())
    return DraftFactSet(
        complaint_id=handoff.complaint_id,
        original_text=handoff.original_text,
        citizen_language=handoff.language,
        issue=LockedFact(value=handoff.issue.value, citizen_words=handoff.issue.source_span, source=handoff.issue.source.value),
        location=LockedFact(
            value=handoff.location.value, citizen_words=handoff.location.source_span, source=handoff.location.source.value
        ),
        location_answers=[
            LockedFact(value=a.text, citizen_words=a.text, source="citizen_clarification")
            for a in classification.answers if a.asked_for == "locality"
        ],
        category_answers=[
            LockedFact(value=a.text, citizen_words=a.text, source="citizen_clarification")
            for a in classification.answers if a.asked_for == "category"
        ],
        duration=(
            LockedFact(value=handoff.duration.value, citizen_words=handoff.duration.source_span, source=handoff.duration.source.value)
            if handoff.duration else None
        ),
        identifiers=[
            LockedFact(value=e.value, citizen_words=e.source_span, source=e.source.value)
            for e in handoff.entities if e.type == "identifier"
        ],
        category=category.category,
        category_record_id=category.id,
        category_name=category.display_name,
        department_id=dept.id,
        department_name=dept.name,
        jurisdiction_id=jurisdiction.jurisdiction_id,
        jurisdiction_name=jurisdiction.name,
        resolved_place=jurisdiction.matched_place,
        location_precision=jurisdiction.location_precision.value,
        source_ids=sorted(sources),
        classification_explanation=classification.explanation,
        service_guideline=classification.service_guideline,
        safety_flags=sorted(set(safety_flags) | set(classification.safety_flags)),
        demo_data=classification.demo_data,
    )
