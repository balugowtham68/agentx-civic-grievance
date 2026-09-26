"""Classification orchestration (Phase 3): API -> ClassificationService -> ClassificationAgent.

The service owns the state machine, persistence (classification_records + the
existing complaints row) and the audit trail. The agent owns the reasoning.

State: UNDERSTOOD --run--> CLASSIFYING --> CLASSIFIED | NEEDS_INFO | NEEDS_REVIEW
       NEEDS_INFO / NEEDS_REVIEW --answer|retry--> CLASSIFYING --> ...
Only complaints whose intake the citizen confirmed can enter classification.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.agents.base import AgentContext
from app.agents.classification import ClassificationAgent
from app.core.clock import Clock, get_clock
from app.core.config import Settings
from app.core.errors import ConflictError, NotFoundError, ServiceUnavailableError
from app.core.state_machine import ensure_transition
from app.models import ClassificationRecord, Complaint
from app.repositories import ClassificationRepository, IntakeRepository
from app.schemas.audit import AuditEventCreate
from app.schemas.classification import (
    ClassificationAnswer,
    ClassificationEvidenceView,
    ClassificationExplanation,
    ClassificationRequest,
    ClassificationResult,
    ClassificationStatus,
    KnowledgeBaseStatus,
)
from app.schemas.enums import ActorType, AuditEventType, ComplaintStatus
from app.schemas.intake import IntakeResult
from app.services.audit_service import AuditService
from app.services.complaint_service import ComplaintService
from app.services.intake.service import NotConfirmedError, build_handoff
from app.services.knowledge import CivicKnowledgeBase, KnowledgeBaseError

_AGENT = "classification"
_RERUN_STATUSES = {ComplaintStatus.NEEDS_INFO, ComplaintStatus.NEEDS_REVIEW}


class KnowledgeBaseUnavailableError(ServiceUnavailableError):
    code = "knowledge_base_unavailable"


class ClassificationService:
    def __init__(
        self,
        session: Session,
        agent: ClassificationAgent,
        knowledge: CivicKnowledgeBase,
        settings: Settings,
        clock: Clock | None = None,
    ) -> None:
        self.clock = clock or get_clock()
        self.agent = agent
        self.knowledge = knowledge
        self.settings = settings
        self.complaints = ComplaintService(session, self.clock)
        self.audit = AuditService(session, self.clock)
        self.records = ClassificationRepository(session)
        self.intake = IntakeRepository(session)

    # ------------------------------------------------------------------ queries

    def get(self, complaint_id: str) -> ClassificationResult:
        self.complaints.get(complaint_id)
        return ClassificationResult.model_validate(self._record(complaint_id).result)

    def evidence(self, complaint_id: str) -> ClassificationEvidenceView:
        result = self.get(complaint_id)
        return ClassificationEvidenceView(
            complaint_id=complaint_id,
            classification_status=result.classification_status,
            evidence=result.evidence,
            rule_matches=result.rule_matches,
            retrieved_sources=result.retrieved_sources,
            source_ids=_source_ids(result),
        )

    def explanation(self, complaint_id: str) -> ClassificationExplanation:
        result = self.get(complaint_id)
        return ClassificationExplanation(
            complaint_id=complaint_id,
            classification_status=result.classification_status,
            explanation=result.explanation,
            reasoning=result.reasoning,
            source_ids=_source_ids(result),
            demo_data=result.demo_data,
        )

    def knowledge_status(self) -> KnowledgeBaseStatus:
        return self.knowledge.status()

    # ------------------------------------------------------------------ commands

    async def run(self, complaint_id: str) -> ClassificationResult:
        complaint = self.complaints.get(complaint_id)
        if self.records.get(complaint_id) is not None:
            raise ConflictError("Classification has already run; answer its question or use retry")
        if complaint.status is not ComplaintStatus.UNDERSTOOD:
            raise NotConfirmedError(
                f"Complaint is {complaint.status.value}; only complaints the citizen confirmed (UNDERSTOOD) can be classified"
            )
        return await self._execute(complaint, None)

    async def retry(self, complaint_id: str) -> ClassificationResult:
        complaint = self.complaints.get(complaint_id)
        record = self.records.get(complaint_id)
        if record is None:
            return await self.run(complaint_id)
        if complaint.status not in _RERUN_STATUSES:
            raise ConflictError(f"Complaint is {complaint.status.value}; classification can only be retried when it needs information or review")
        return await self._execute(complaint, record)

    async def answer(self, complaint_id: str, text: str) -> ClassificationResult:
        complaint = self.complaints.get(complaint_id)
        record = self._record(complaint_id)
        previous = ClassificationResult.model_validate(record.result)
        if complaint.status not in _RERUN_STATUSES or not previous.clarification_questions:
            raise ConflictError("There is no open classification question for this complaint")
        asked_for = previous.clarification_questions[0].field
        answer = ClassificationAnswer(
            text=text, asked_for="locality" if asked_for == "locality" else "category", recorded_at=self.clock.now()
        )
        record.answers = [*record.answers, answer.model_dump(mode="json")]
        self._event(
            complaint_id, AuditEventType.CLASSIFICATION_ANSWERED,
            f"Citizen answered the {answer.asked_for} question",
            actor=ActorType.CITIZEN,
            payload={"asked_for": answer.asked_for, "answer_number": len(record.answers), "characters": len(text)},
            evidence=[{"field": answer.asked_for, "citizen_words": text, "source": "citizen_clarification"}],
        )
        return await self._execute(complaint, record)

    # ------------------------------------------------------------------ internals

    def _record(self, complaint_id: str) -> ClassificationRecord:
        record = self.records.get(complaint_id)
        if record is None:
            raise NotFoundError(f"Complaint {complaint_id!r} has not been classified yet")
        return record

    async def _execute(self, complaint: Complaint, record: ClassificationRecord | None) -> ClassificationResult:
        intake_record = self.intake.get(complaint.id)
        if intake_record is None:
            raise NotConfirmedError("The complaint has not been through intake")
        intake = IntakeResult.model_validate(intake_record.result)
        handoff = build_handoff(complaint, intake)  # refuses anything the citizen has not confirmed
        try:
            kb_status = self.knowledge.ensure_ready(auto_ingest=self.settings.kb_auto_ingest)
        except KnowledgeBaseError as exc:
            raise KnowledgeBaseUnavailableError(str(exc)) from exc

        now = self.clock.now()
        ensure_transition(complaint.status, ComplaintStatus.CLASSIFYING)
        complaint.status = ComplaintStatus.CLASSIFYING
        complaint.updated_at = now
        runs = (record.runs if record else 0) + 1
        self._event(
            complaint.id, AuditEventType.CLASSIFICATION_STARTED,
            f"Classification started (run {runs}) from the confirmed Phase 2 handoff",
            payload={"run": runs, "knowledge_base_version": kb_status.fingerprint, "records": kb_status.records,
                     "embedder": kb_status.embedder, "language": handoff.language},
        )
        answers = [ClassificationAnswer.model_validate(a) for a in (record.answers if record else [])]
        result = await self.agent.execute(
            ClassificationRequest(handoff=handoff, answers=answers, safety_flags=intake.safety_flags),
            AgentContext(complaint_id=complaint.id, clock=self.clock),
        )
        return self._persist(complaint, record, result, runs)

    def _persist(
        self, complaint: Complaint, record: ClassificationRecord | None, result: ClassificationResult, runs: int
    ) -> ClassificationResult:
        now = self.clock.now()
        if record is None:
            record = ClassificationRecord(complaint_id=complaint.id, answers=[], created_at=now)
        result = result.model_copy(update={"created_at": record.created_at, "updated_at": now})
        record.classification_status = result.classification_status
        record.confidence_state = result.confidence_state
        record.category = result.category
        record.department_id = result.responsible_department.department_id if result.responsible_department else None
        record.jurisdiction_id = result.jurisdiction.jurisdiction_id
        record.processing_mode = result.processing_mode
        record.missing_information = result.missing_information
        record.source_ids = _source_ids(result)
        record.knowledge_base_version = result.knowledge_base_version
        record.result = result.model_dump(mode="json")
        record.runs = runs
        record.updated_at = now
        self.records.save(record)

        ensure_transition(complaint.status, result.status)
        complaint.status = result.status
        classified = result.classification_status is ClassificationStatus.CLASSIFIED
        complaint.category = result.category if classified else None
        complaint.department_id = record.department_id if classified else None
        complaint.jurisdiction_id = record.jurisdiction_id if classified else None
        complaint.updated_at = now
        self._audit(complaint.id, result)
        return result

    def _event(
        self,
        complaint_id: str,
        event_type: AuditEventType,
        summary: str,
        *,
        actor: ActorType = ActorType.AGENT,
        payload: dict[str, object] | None = None,
        evidence: list[dict[str, object]] | None = None,
    ) -> None:
        self.audit.record(
            AuditEventCreate(
                complaint_id=complaint_id,
                event_type=event_type,
                actor_type=actor,
                actor_name="citizen" if actor is ActorType.CITIZEN else _AGENT,
                summary=summary[:500],
                payload=payload or {},
                evidence=evidence or [],
            )
        )

    def _audit(self, complaint_id: str, result: ClassificationResult) -> None:
        mode = result.processing_mode.value
        sources = _source_ids(result)
        self._event(
            complaint_id, AuditEventType.KNOWLEDGE_RETRIEVED,
            f"Retrieved {len(result.retrieved_sources)} civic knowledge record(s) locally",
            payload={"processing_mode": mode, "source_ids": sorted({r.record_id for r in result.retrieved_sources}),
                     "doc_ids": [r.doc_id for r in result.retrieved_sources],
                     "provider": next((s.provider for s in result.provider_trace if s.stage == "retrieval"), None)},
        )
        self._event(
            complaint_id, AuditEventType.CLASSIFICATION_CANDIDATES_GENERATED,
            "Candidates: " + (", ".join(f"{c.category} ({c.decision})" for c in result.candidates) or "none"),
            payload={"processing_mode": mode,
                     "candidates": [c.model_dump(mode="json", exclude={"best_similarity"}) for c in result.candidates]},
        )
        if result.rule_matches:
            self._event(
                complaint_id, AuditEventType.CLASSIFICATION_RULE_MATCHED,
                "Configured rules matched: " + ", ".join(sorted({m.rule_id for m in result.rule_matches})),
                payload={"processing_mode": mode, "source_ids": sorted({m.rule_id for m in result.rule_matches})},
                evidence=[m.model_dump(mode="json") for m in result.rule_matches],
            )
        if result.rejected_ai_output:
            self._event(
                complaint_id, AuditEventType.CLASSIFICATION_REJECTED,
                "Rejected unsupported output: " + "; ".join(result.rejected_ai_output),
                payload={"processing_mode": mode, "reasons": result.rejected_ai_output},
            )
        status = result.classification_status
        evidence = [e.model_dump(mode="json") for e in result.evidence]
        common = {"processing_mode": mode, "source_ids": sources, "confidence_state": result.confidence_state.value}
        if status is ClassificationStatus.CLASSIFIED:
            dept = result.responsible_department
            self._event(
                complaint_id, AuditEventType.CLASSIFICATION_COMPLETED,
                f"Classified as {result.category} -> {dept.department_id if dept else '-'} / "
                f"{result.jurisdiction.jurisdiction_id or 'no jurisdiction'}",
                payload={**common, "category": result.category, "department_id": dept.department_id if dept else None,
                         "jurisdiction_id": result.jurisdiction.jurisdiction_id},
                evidence=evidence,
            )
            self._event(complaint_id, AuditEventType.COMPLAINT_CLASSIFIED, "Complaint CLASSIFIED",
                        payload={"processing_mode": mode, "category": result.category})
        elif status is ClassificationStatus.NEEDS_INFO:
            self._event(
                complaint_id, AuditEventType.CLASSIFICATION_NEEDS_INFO,
                "Needs: " + ", ".join(result.missing_information),
                payload={**common, "missing": result.missing_information,
                         "questions": [q.model_dump(mode="json") for q in result.clarification_questions]},
                evidence=evidence,
            )
        elif status is ClassificationStatus.AMBIGUOUS:
            self._event(
                complaint_id, AuditEventType.CLASSIFICATION_AMBIGUOUS,
                "Ambiguous between: " + ", ".join(c.category for c in result.candidates if c.decision in {"ambiguous", "suggested"}),
                payload={**common, "questions": [q.model_dump(mode="json") for q in result.clarification_questions]},
                evidence=evidence,
            )
        else:
            self._event(
                complaint_id, AuditEventType.CLASSIFICATION_REJECTED,
                "UNSUPPORTED_CLASSIFICATION: " + result.explanation[:400],
                payload=common,
                evidence=evidence,
            )
            self._event(complaint_id, AuditEventType.COMPLAINT_NEEDS_REVIEW,
                        "Complaint needs review: classification is not grounded in the knowledge base",
                        payload={"processing_mode": mode})


def _source_ids(result: ClassificationResult) -> list[str]:
    ids = {e.source for e in result.evidence if e.kind == "knowledge"}
    ids |= {m.rule_id for m in result.rule_matches}
    if result.responsible_department:
        ids.add(result.responsible_department.source_id)
    if result.jurisdiction.source_id:
        ids.add(result.jurisdiction.source_id)
    return sorted(ids)
