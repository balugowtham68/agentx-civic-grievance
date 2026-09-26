"""Classification & Reasoning endpoints (Phase 3). Routes only translate HTTP to
ClassificationService calls; the service enforces confirmation and state."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import ClassificationServiceDep
from app.api.params import ComplaintId
from app.core.errors import ErrorResponse
from app.schemas.classification import (
    ClassificationEvidenceView,
    ClassificationExplanation,
    ClassificationResult,
    KnowledgeBaseStatus,
)
from app.schemas.intake import ClarificationAnswerRequest

router = APIRouter(prefix="/classification", tags=["classification"])



def _errors(*codes: int) -> dict[int | str, dict[str, object]]:
    return {code: {"model": ErrorResponse} for code in codes}


@router.get("/knowledge-base", response_model=KnowledgeBaseStatus)
def knowledge_base_status(service: ClassificationServiceDep) -> KnowledgeBaseStatus:
    """Local civic knowledge base readiness: records, embedder, stale check. No content, no embeddings."""
    return service.knowledge_status()


@router.post("/{complaint_id}/run", response_model=ClassificationResult, responses=_errors(404, 409, 422, 503))
async def run_classification(complaint_id: ComplaintId, service: ClassificationServiceDep) -> ClassificationResult:
    """Classify a complaint the citizen has confirmed (UNDERSTOOD). 409 for anything else."""
    return await service.run(complaint_id)


@router.get("/{complaint_id}", response_model=ClassificationResult, responses=_errors(404, 422))
def get_classification(complaint_id: ComplaintId, service: ClassificationServiceDep) -> ClassificationResult:
    return service.get(complaint_id)


@router.post("/{complaint_id}/retry", response_model=ClassificationResult, responses=_errors(404, 409, 422, 503))
async def retry_classification(complaint_id: ComplaintId, service: ClassificationServiceDep) -> ClassificationResult:
    """Re-run classification (e.g. after the knowledge base was updated) for NEEDS_INFO / NEEDS_REVIEW."""
    return await service.retry(complaint_id)


@router.post("/{complaint_id}/answer", response_model=ClassificationResult, responses=_errors(404, 409, 422, 503))
async def answer_classification(
    complaint_id: ComplaintId, body: ClarificationAnswerRequest, service: ClassificationServiceDep
) -> ClassificationResult:
    """Citizen answers the open classification question (locality or category); classification re-runs."""
    return await service.answer(complaint_id, body.text)


@router.get("/{complaint_id}/evidence", response_model=ClassificationEvidenceView, responses=_errors(404, 422))
def classification_evidence(complaint_id: ComplaintId, service: ClassificationServiceDep) -> ClassificationEvidenceView:
    """Citizen evidence, matched rules and retrieved knowledge records (with provenance)."""
    return service.evidence(complaint_id)


@router.get("/{complaint_id}/explanation", response_model=ClassificationExplanation, responses=_errors(404, 422))
def classification_explanation(complaint_id: ComplaintId, service: ClassificationServiceDep) -> ClassificationExplanation:
    """Plain-language explanation built only from the evidence and retrieved knowledge."""
    return service.explanation(complaint_id)
