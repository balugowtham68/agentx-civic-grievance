"""Complaint drafting orchestration (Phase 4): API -> DraftingService -> DraftingAgent.

The service owns preconditions, the state machine, versioned persistence and the
audit trail. It reads Phase 2 (confirmed handoff) and Phase 3 (classification
record) without changing them.

State: CLASSIFIED --run--> DRAFTING (v1, awaiting review) --approve--> DRAFTED
       DRAFTING/DRAFTED --edit--> DRAFTING (new version, previous versions kept)
Nothing here files, tracks, monitors or escalates.
"""

from __future__ import annotations

from uuid import uuid4

from sqlalchemy.orm import Session

from app.agents.base import AgentContext
from app.agents.drafting import DraftingAgent
from app.agents.drafting.agent import DraftValidationError
from app.agents.drafting.facts import NotClassifiedError, build_fact_set
from app.core.clock import Clock, get_clock
from app.core.errors import AppError, ConflictError, NotFoundError
from app.core.state_machine import ensure_transition
from app.models import Complaint, DraftRecord
from app.repositories import ClassificationRepository, DraftRepository, IntakeRepository
from app.schemas.agents import DraftedComplaint
from app.schemas.audit import AuditEventCreate
from app.schemas.classification import ClassificationResult
from app.schemas.drafting import (
    ComplaintDraft,
    DraftApproveRequest,
    DraftEditRequest,
    DraftFactSet,
    DraftingRequest,
    DraftOrigin,
    DraftRunRequest,
    DraftSummary,
    DraftValidationStatus,
    DraftView,
    ReviewStatus,
)
from app.schemas.enums import ActorType, AuditEventType, ComplaintStatus
from app.schemas.intake import IntakeResult
from app.services.audit_service import AuditService
from app.services.complaint_service import ComplaintService
from app.services.intake.service import NotConfirmedError, build_handoff

_AGENT = "drafting"
_EDITABLE = {ComplaintStatus.DRAFTING, ComplaintStatus.DRAFTED}


class DraftEditRejectedError(AppError):
    status_code = 422
    code = "draft_edit_rejected"


class DraftingService:
    def __init__(self, session: Session, agent: DraftingAgent, clock: Clock | None = None) -> None:
        self.session = session
        self.clock = clock or get_clock()
        self.agent = agent
        self.complaints = ComplaintService(session, self.clock)
        self.audit = AuditService(session, self.clock)
        self.drafts = DraftRepository(session)
        self.intake = IntakeRepository(session)
        self.classifications = ClassificationRepository(session)

    # ------------------------------------------------------------------ queries

    def get(self, complaint_id: str) -> DraftView:
        complaint = self.complaints.get(complaint_id)
        versions = self.drafts.versions(complaint_id)
        if not versions:
            raise NotFoundError(f"Complaint {complaint_id!r} has no draft yet")
        return DraftView(
            complaint_id=complaint_id,
            status=complaint.status,
            current=ComplaintDraft.model_validate(versions[-1].draft),
            versions=[_summary(v) for v in versions],
            approved_version=next((v.version for v in versions if v.review_status is ReviewStatus.APPROVED), None),
        )

    def version(self, complaint_id: str, version: int) -> ComplaintDraft:
        self.complaints.get(complaint_id)
        record = self.drafts.get_version(complaint_id, version)
        if record is None:
            raise NotFoundError(f"Draft version {version} does not exist")
        return ComplaintDraft.model_validate(record.draft)

    # ------------------------------------------------------------------ commands

    async def run(self, complaint_id: str, request: DraftRunRequest) -> DraftView:
        complaint = self.complaints.get(complaint_id)
        if self.drafts.latest(complaint_id) is not None:
            raise ConflictError("A draft already exists; review, edit or approve it")
        facts = self._facts(complaint)

        draft_id = str(uuid4())
        try:
            result = await self.agent.execute(
                DraftingRequest(facts=facts, draft_language=request.draft_language, draft_id=draft_id, version=1),
                AgentContext(complaint_id=complaint_id, clock=self.clock),
            )
        except DraftValidationError as exc:
            self._event(complaint_id, AuditEventType.DRAFTING_VALIDATION_FAILED, "Template draft failed validation; nothing saved",
                        payload={"reason": exc.message[:400]})
            self.session.commit()  # keep the audit record; the complaint stays CLASSIFIED
            raise

        self._event(complaint_id, AuditEventType.DRAFTING_STARTED, "Drafting started from the classified complaint",
                    payload={"draft_language": request.draft_language, "category": facts.category})
        ensure_transition(complaint.status, ComplaintStatus.DRAFTING)
        complaint.status = ComplaintStatus.DRAFTING
        complaint.updated_at = self.clock.now()
        self._event(
            complaint_id, AuditEventType.DRAFTING_SOURCE_LOADED,
            "Loaded confirmed Phase 2 facts and the Phase 3 classification (fact-locked)",
            payload={"category": facts.category, "department_id": facts.department_id,
                     "jurisdiction_id": facts.jurisdiction_id, "source_ids": facts.source_ids,
                     "citizen_language": facts.citizen_language, "has_duration": facts.duration is not None},
        )
        draft = result.draft
        trace = [s.model_dump(mode="json") for s in result.provider_trace]
        self._event(
            complaint_id, AuditEventType.DRAFTING_GENERATED,
            f"Draft v1 generated ({draft.processing_mode.value})",
            payload={"version": 1, "processing_mode": draft.processing_mode.value, "provider_trace": trace,
                     "validation_status": draft.validation_status.value},
        )
        if result.rejected_ai_output:
            self._event(complaint_id, AuditEventType.DRAFTING_VALIDATION_FAILED,
                        "Optional AI wording rejected",
                        payload={"reasons": result.rejected_ai_output})
            self._event(complaint_id, AuditEventType.DRAFTING_FALLBACK,
                        "Deterministic template draft used instead of the optional AI wording",
                        payload={"version": 1, "validation_status": draft.validation_status.value})
        self._event(complaint_id, AuditEventType.DRAFTING_VALIDATION_PASSED,
                    f"Draft v1 passed validation ({draft.validation_status.value})",
                    payload={"version": 1, "validation_status": draft.validation_status.value})
        self._store(draft, facts)
        return self.get(complaint_id)

    def edit(self, complaint_id: str, request: DraftEditRequest) -> DraftView:
        complaint = self.complaints.get(complaint_id)
        if complaint.status not in _EDITABLE:
            raise ConflictError(f"Complaint is {complaint.status.value}; only a generated draft can be edited")
        latest = self._latest(complaint_id)
        if request.based_on_version != latest.version:
            raise ConflictError(f"The draft changed: edit version {latest.version}, not {request.based_on_version}")
        previous = ComplaintDraft.model_validate(latest.draft)
        facts = DraftFactSet.model_validate(latest.facts)
        changes = {k: v for k, v in request.model_dump(exclude={"based_on_version"}).items() if v is not None}
        changed = [k for k, v in changes.items() if getattr(previous.sections, k) != v]
        if not changed:
            raise DraftEditRejectedError("Nothing changed in the draft")
        sections = previous.sections.model_copy(update=changes)
        report = self.agent.validator.validate(
            sections, self.agent.body(sections, facts, statement=False), facts, mode="citizen_edit"
        )
        if report.hard:
            self._event(complaint_id, AuditEventType.DRAFTING_VALIDATION_FAILED, "Citizen edit rejected; draft unchanged",
                        actor=ActorType.CITIZEN, payload={"fields": changed, "reasons": report.hard})
            self.session.commit()
            raise DraftEditRejectedError("This edit cannot be saved: " + "; ".join(report.hard))
        status = DraftValidationStatus.NEEDS_REVIEW if report.citizen_added else DraftValidationStatus.VALID
        version = latest.version + 1
        draft = self.agent.assemble(
            facts, sections, draft_id=str(uuid4()), version=version, origin=DraftOrigin.CITIZEN_EDIT,
            based_on=latest.version, status=status, issues=[], mode=previous.processing_mode,
            draft_language=previous.draft_language, created_by="citizen", now=self.clock.now(),
            citizen_added=report.citizen_added,
        )
        if complaint.status is ComplaintStatus.DRAFTED:  # an approved draft was changed: approval withdrawn
            ensure_transition(complaint.status, ComplaintStatus.DRAFTING)
            complaint.status = ComplaintStatus.DRAFTING
            complaint.drafted_complaint = None
            approved = next((v for v in self.drafts.versions(complaint_id) if v.review_status is ReviewStatus.APPROVED), None)
            if approved is not None:  # keep the version intact; only its review state changes
                approved.review_status = ReviewStatus.SUPERSEDED
                approved.draft = {**approved.draft, "review_status": ReviewStatus.SUPERSEDED.value}
                approved.updated_at = self.clock.now()
                self._event(complaint_id, AuditEventType.DRAFTING_APPROVAL_WITHDRAWN,
                            f"Approval of v{approved.version} withdrawn: the citizen edited the draft",
                            actor=ActorType.CITIZEN, payload={"approved_version": approved.version, "new_version": version})
        complaint.updated_at = self.clock.now()
        self._event(complaint_id, AuditEventType.DRAFTING_EDITED, f"Citizen edited: {', '.join(changed)}",
                    actor=ActorType.CITIZEN,
                    payload={"fields": changed, "based_on_version": latest.version, "validation_status": status.value,
                             "citizen_added_items": len(report.citizen_added)})
        self._event(complaint_id, AuditEventType.DRAFTING_VALIDATION_PASSED, f"Draft v{version} validated ({status.value})",
                    payload={"version": version, "validation_status": status.value})
        self._store(draft, facts)
        return self.get(complaint_id)

    def approve(self, complaint_id: str, request: DraftApproveRequest) -> DraftView:
        complaint = self.complaints.get(complaint_id)
        latest = self._latest(complaint_id)
        if complaint.status is not ComplaintStatus.DRAFTING:
            raise ConflictError(f"Complaint is {complaint.status.value}; there is no draft awaiting review")
        if request.version != latest.version:
            raise ConflictError(f"Only the latest version ({latest.version}) can be approved")
        draft = ComplaintDraft.model_validate(latest.draft)
        if draft.validation_status is DraftValidationStatus.INVALID:  # defensive: never stored
            raise ConflictError("An invalid draft cannot be approved")
        now = self.clock.now()
        draft = draft.model_copy(update={"review_status": ReviewStatus.APPROVED})
        latest.draft = draft.model_dump(mode="json")
        latest.review_status = ReviewStatus.APPROVED
        latest.updated_at = now
        ensure_transition(complaint.status, ComplaintStatus.DRAFTED)
        complaint.status = ComplaintStatus.DRAFTED
        complaint.drafted_complaint = _for_filing(draft, DraftFactSet.model_validate(latest.facts)).model_dump(mode="json")
        complaint.updated_at = now
        self._event(complaint_id, AuditEventType.DRAFTING_APPROVED, f"Citizen approved draft v{draft.version}",
                    actor=ActorType.CITIZEN,
                    payload={"version": draft.version, "draft_id": draft.draft_id,
                             "validation_status": draft.validation_status.value, "origin": draft.origin.value,
                             "citizen_added_items": len(draft.citizen_added_information)})
        self._event(complaint_id, AuditEventType.DRAFTING_COMPLETED, f"Drafting completed with approved v{draft.version}",
                    payload={"version": draft.version, "processing_mode": draft.processing_mode.value})
        self._event(complaint_id, AuditEventType.COMPLAINT_DRAFTED, "Complaint DRAFTED (citizen-approved; not filed)",
                    payload={"version": draft.version, "processing_mode": draft.processing_mode.value})
        return self.get(complaint_id)

    # ------------------------------------------------------------------ internals

    def _facts(self, complaint: Complaint) -> DraftFactSet:
        intake_record = self.intake.get(complaint.id)
        if intake_record is None:
            raise NotConfirmedError("The complaint has not been through intake")
        intake = IntakeResult.model_validate(intake_record.result)
        handoff = build_handoff(complaint, intake)  # 409 unless the citizen confirmed
        record = self.classifications.get(complaint.id)
        if record is None:
            raise NotClassifiedError("Draft unavailable. Reason: the complaint has not been classified yet.")
        classification = ClassificationResult.model_validate(record.result)
        facts = build_fact_set(handoff, classification, self.agent.reference.data, safety_flags=intake.safety_flags)
        if complaint.status is not ComplaintStatus.CLASSIFIED:
            raise NotClassifiedError(f"Draft unavailable. Reason: the complaint is {complaint.status.value}, not CLASSIFIED.")
        return facts

    def _latest(self, complaint_id: str) -> DraftRecord:
        latest = self.drafts.latest(complaint_id)
        if latest is None:
            raise NotFoundError(f"Complaint {complaint_id!r} has no draft yet")
        return latest

    def _store(self, draft: ComplaintDraft, facts: DraftFactSet) -> None:
        now = self.clock.now()
        self.drafts.add(DraftRecord(
            id=draft.draft_id, complaint_id=draft.complaint_id, version=draft.version, origin=draft.origin,
            based_on_version=draft.based_on_version, subject=draft.sections.subject, body=draft.body,
            language=draft.citizen_language, draft_language=draft.draft_language,
            processing_mode=draft.processing_mode, validation_status=draft.validation_status,
            review_status=draft.review_status, source_ids=draft.source_ids,
            draft=draft.model_dump(mode="json"), facts=facts.model_dump(mode="json"),
            created_by=draft.created_by, created_at=now, updated_at=now,
        ))
        self._event(draft.complaint_id, AuditEventType.DRAFTING_VERSION_CREATED,
                    f"Draft version {draft.version} saved ({draft.origin.value})",
                    actor=ActorType.CITIZEN if draft.created_by == "citizen" else ActorType.AGENT,
                    payload={"version": draft.version, "draft_id": draft.draft_id, "origin": draft.origin.value,
                             "based_on_version": draft.based_on_version, "source_ids": draft.source_ids,
                             "processing_mode": draft.processing_mode.value})

    def _event(
        self,
        complaint_id: str,
        event_type: AuditEventType,
        summary: str,
        *,
        actor: ActorType = ActorType.AGENT,
        payload: dict[str, object] | None = None,
    ) -> None:
        self.audit.record(AuditEventCreate(
            complaint_id=complaint_id, event_type=event_type, actor_type=actor,
            actor_name="citizen" if actor is ActorType.CITIZEN else _AGENT, summary=summary[:500],
            payload=payload or {},
        ))


def _summary(record: DraftRecord) -> DraftSummary:
    return DraftSummary(
        version=record.version, origin=record.origin, validation_status=record.validation_status,
        review_status=record.review_status, subject=record.subject, generated_at=record.created_at,
        created_by=record.created_by,
    )


def _for_filing(draft: ComplaintDraft, facts: DraftFactSet) -> DraftedComplaint:
    return DraftedComplaint(
        issue=draft.sections.issue_text,
        category=draft.category,
        department_id=draft.department_id,
        jurisdiction_id=draft.jurisdiction_id,
        location=draft.sections.location_text,
        duration=draft.duration,
        description=draft.sections.summary,
        requested_action=draft.sections.requested_action,
        supporting_details=draft.supporting_facts,
        original_text=facts.original_text,
        subject=draft.sections.subject,
        body=draft.body,
        draft_id=draft.draft_id,
        draft_version=draft.version,
    )
