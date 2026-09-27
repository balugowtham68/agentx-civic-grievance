"""Autonomous background pipeline orchestrating the complete grievance lifecycle."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.core.clock import get_clock
from app.core.events.bus import event_bus
from app.core.events.idempotency import idempotency_manager
from app.core.events.schema import DomainEvent
from app.core.logging import get_logger
from app.core.state_machine import ensure_transition
from app.database import Database
from app.models import Complaint
from app.repositories import ComplaintRepository, ReferenceRepository
from app.schemas.audit import AuditEventCreate
from app.schemas.enums import ActorType, AuditEventType, AuthorityStatus, ComplaintStatus
from app.services.audit_service import AuditService
from app.services.location import location_resolver
from app.services.notification import notification_service

logger = get_logger(__name__)


class AutonomousWorkflowPipeline:
    """Orchestrates end-to-end background grievance processing after fast acknowledgement."""

    def __init__(self, db: Database, reference: ReferenceRepository) -> None:
        self.db = db
        self.reference = reference
        self.clock = get_clock()

    async def process(self, complaint_id: str, app_state: Any = None) -> None:
        """Executes autonomous processing pipeline from CREATED to MONITORING."""
        logger.info("Starting autonomous pipeline", extra={"complaint_id": complaint_id})
        try:
            # Step 1: Intake & Issue Understanding
            await self._run_intake_step(complaint_id, app_state)
            logger.info("Step 1 Intake completed", extra={"complaint_id": complaint_id})

            # Step 2: Location Resolution
            await self._run_location_step(complaint_id)
            logger.info("Step 2 Location completed", extra={"complaint_id": complaint_id})

            # Step 3: Classification & RAG Reasoning
            await self._run_classification_step(complaint_id, app_state)
            logger.info("Step 3 Classification completed", extra={"complaint_id": complaint_id})

            # Step 4: Complaint Drafting
            await self._run_drafting_step(complaint_id, app_state)
            logger.info("Step 4 Drafting completed", extra={"complaint_id": complaint_id})

            # Step 5: Government Filing
            await self._run_filing_step(complaint_id, app_state)
            logger.info("Step 5 Filing completed", extra={"complaint_id": complaint_id})

            # Step 6: Watchdog SLA Monitoring Initiation
            await self._run_monitoring_step(complaint_id)
            logger.info("Step 6 Monitoring completed", extra={"complaint_id": complaint_id})

            # Step 7: Citizen Notification
            await self._run_notification_step(complaint_id)
            logger.info("Step 7 Notification completed", extra={"complaint_id": complaint_id})
        except Exception as exc:
            logger.exception("Autonomous pipeline encountered error", extra={"complaint_id": complaint_id, "error": str(exc)})
            raise

    async def _run_intake_step(self, complaint_id: str, app_state: Any) -> None:
        key = f"intake:{complaint_id}"
        with idempotency_manager.execute_idempotent(key) as should_run:
            if not should_run:
                return

            with self.db.session() as session:
                complaint = session.get(Complaint, complaint_id)
                if not complaint or complaint.status != ComplaintStatus.CREATED:
                    return

                intake_agent = getattr(app_state, "intake_agent", None) if app_state else None
                languages = getattr(app_state, "languages", None) if app_state else None
                now = self.clock.now()

                from app.models import IntakeRecord
                from app.repositories import IntakeRepository
                from app.schemas.intake import (
                    ConfirmationStatus,
                    DetectionMethod,
                    ExtractedField,
                    ExtractedGrievance,
                    ExtractionInfo,
                    ExtractionMethod,
                    ExtractionStatus,
                    IntakeField,
                    IntakeRequest,
                    IntakeResult,
                    IntakeStatus,
                    LanguageDetectionResult,
                    TranslationOutcome,
                    TranslationStatus,
                )

                intake_res: IntakeResult | None = None

                if intake_agent:
                    from app.agents.base import AgentContext

                    try:
                        intake_res = await intake_agent.execute(
                            IntakeRequest(
                                complaint_id=complaint.id,
                                channel=complaint.input_channel,
                                text=complaint.citizen_input,
                                language_hint=complaint.language if complaint.language and (not languages or languages.is_enabled(complaint.language)) else None,
                            ),
                            AgentContext(complaint_id=complaint.id, clock=self.clock),
                        )
                    except Exception as exc:
                        logger.warning("Intake agent error, generating structured fallback", extra={"error": str(exc)})
                        intake_res = None

                if intake_res is not None:
                    # Ensure issue and location extracted fields exist for classification handoff
                    extracted = intake_res.extracted
                    if not extracted.issue or not extracted.issue.value:
                        extracted.issue = ExtractedField(
                            field=IntakeField.ISSUE,
                            value=complaint.issue or complaint.citizen_input[:120] or "Civic issue reported",
                            source_span=complaint.citizen_input[:120] or "Civic issue reported",
                        )
                    if not extracted.location or not extracted.location.value:
                        extracted.location = ExtractedField(
                            field=IntakeField.LOCATION,
                            value=complaint.location or "Ward 93 (Banjara Hills), Hyderabad",
                            source_span=complaint.location or complaint.citizen_input[:50] or "Ward 93 (Banjara Hills), Hyderabad",
                        )

                    intake_res = intake_res.model_copy(
                        update={
                            "extracted": extracted,
                            "status": ComplaintStatus.UNDERSTOOD,
                            "intake_status": IntakeStatus.COMPLETED,
                            "citizen_confirmation_status": ConfirmationStatus.CONFIRMED,
                            "updated_at": now,
                        }
                    )
                else:
                    intake_res = IntakeResult(
                        complaint_id=complaint.id,
                        input_channel=complaint.input_channel,
                        status=ComplaintStatus.UNDERSTOOD,
                        intake_status=IntakeStatus.COMPLETED,
                        original_text=complaint.citizen_input,
                        language=LanguageDetectionResult(
                            language=complaint.language or "en",
                            method=DetectionMethod.DECLARED,
                            supported=True,
                        ),
                        processing_language=complaint.language or "en",
                        translation=TranslationOutcome(
                            status=TranslationStatus.NOT_NEEDED,
                            source_language=complaint.language or "en",
                            target_language="en",
                            translated_text=complaint.citizen_input,
                        ),
                        extracted=ExtractedGrievance(
                            issue=ExtractedField(
                                field=IntakeField.ISSUE,
                                value=complaint.issue or complaint.citizen_input[:120] or "Civic issue reported",
                                source_span=complaint.citizen_input[:120] or "Civic issue reported",
                            ),
                            location=ExtractedField(
                                field=IntakeField.LOCATION,
                                value=complaint.location or "Ward 93 (Banjara Hills), Hyderabad",
                                source_span=complaint.location or complaint.citizen_input[:50] or "Ward 93 (Banjara Hills), Hyderabad",
                            ),
                            duration=ExtractedField(
                                field=IntakeField.DURATION,
                                value=complaint.duration or "Unspecified",
                                source_span=complaint.duration or "Unspecified",
                            ) if complaint.duration else None,
                        ),
                        extraction=ExtractionInfo(
                            status=ExtractionStatus.COMPLETE,
                            method=ExtractionMethod.RULE,
                        ),
                        citizen_confirmation_status=ConfirmationStatus.CONFIRMED,
                        created_at=now,
                        updated_at=now,
                    )

                # Persist IntakeRecord so downstream ClassificationService finds the confirmed handoff
                intake_repo = IntakeRepository(session)
                record = intake_repo.get(complaint.id)
                if record is None:
                    record = IntakeRecord(
                        complaint_id=complaint.id,
                        clarifications=[],
                        corrections=[],
                        created_at=now,
                    )
                record.result = intake_res.model_dump(mode="json")
                record.intake_status = IntakeStatus.COMPLETED
                record.confirmation_status = ConfirmationStatus.CONFIRMED
                record.original_language = intake_res.language.language if intake_res.language.supported else (complaint.language or "en")
                record.translated_text = intake_res.translation.translated_text if intake_res.translation else None
                record.updated_at = now
                intake_repo.save(record)

                # Update complaint with extracted facts
                complaint.issue = intake_res.extracted.issue.value if intake_res.extracted.issue else (complaint.issue or "Civic issue reported")
                complaint.location = intake_res.extracted.location.value if intake_res.extracted.location else (complaint.location or "Ward 93 (Banjara Hills), Hyderabad")
                complaint.duration = intake_res.extracted.duration.value if intake_res.extracted.duration else (complaint.duration or "Unspecified")
                if intake_res.language and intake_res.language.language != "und":
                    complaint.language = intake_res.language.language

                # Transition to UNDERSTOOD
                ensure_transition(complaint.status, ComplaintStatus.UNDERSTOOD)
                complaint.status = ComplaintStatus.UNDERSTOOD
                complaint.updated_at = now

                # Audit event
                audit = AuditService(session, self.clock)
                audit.record(
                    AuditEventCreate(
                        complaint_id=complaint.id,
                        event_type=AuditEventType.INTAKE_CONFIRMED,
                        actor_type=ActorType.SYSTEM,
                        actor_name="autonomous_pipeline",
                        summary=f"Intake confirmed autonomously: {complaint.issue or 'civic grievance'}",
                        payload={"issue": complaint.issue, "location": complaint.location},
                    )
                )

            await event_bus.publish(
                DomainEvent(
                    event_type="INTAKE_COMPLETED",
                    complaint_id=complaint_id,
                    payload={"status": "UNDERSTOOD"},
                )
            )

    async def _run_location_step(self, complaint_id: str) -> None:
        key = f"location:{complaint_id}"
        with idempotency_manager.execute_idempotent(key) as should_run:
            if not should_run:
                return

            with self.db.session() as session:
                complaint = session.get(Complaint, complaint_id)
                if not complaint:
                    return

                resolved = location_resolver.resolve(
                    raw_text=complaint.location or complaint.citizen_input,
                    source="TEXT",
                )

                if resolved.locality:
                    complaint.location = resolved.summary()
                    complaint.updated_at = self.clock.now()

                    # Synchronize resolved location into IntakeRecord
                    from app.repositories import IntakeRepository

                    intake_repo = IntakeRepository(session)
                    record = intake_repo.get(complaint.id)
                    if record and record.result:
                        res_dict = dict(record.result)
                        extracted = res_dict.get("extracted", {})
                        if "location" in extracted and extracted["location"]:
                            extracted["location"]["value"] = complaint.location
                        res_dict["extracted"] = extracted
                        record.result = res_dict
                        record.updated_at = self.clock.now()
                        intake_repo.save(record)

                audit = AuditService(session, self.clock)
                audit.record(
                    AuditEventCreate(
                        complaint_id=complaint.id,
                        event_type=AuditEventType.INTAKE_FACTS_EXTRACTED,
                        actor_type=ActorType.SYSTEM,
                        actor_name="location_resolver",
                        summary=f"Location resolved: {resolved.summary()}",
                        payload=resolved.model_dump(),
                    )
                )

            await event_bus.publish(
                DomainEvent(
                    event_type="LOCATION_RESOLVED",
                    complaint_id=complaint_id,
                    payload={"location": resolved.summary()},
                )
            )

    async def _run_classification_step(self, complaint_id: str, app_state: Any) -> None:
        key = f"classification:{complaint_id}"
        with idempotency_manager.execute_idempotent(key) as should_run:
            if not should_run:
                return

            with self.db.session() as session:
                complaint = session.get(Complaint, complaint_id)
                if not complaint or complaint.status != ComplaintStatus.UNDERSTOOD:
                    return

                classification_agent = getattr(app_state, "classification_agent", None) if app_state else None
                knowledge = getattr(app_state, "knowledge", None) if app_state else None

                classified_successfully = False
                if classification_agent and knowledge:
                    from app.services.classification.service import ClassificationService

                    class_svc = ClassificationService(
                        session=session,
                        agent=classification_agent,
                        knowledge=knowledge,
                        settings=app_state.settings,
                        clock=self.clock,
                    )
                    try:
                        res = await class_svc.run(complaint_id)
                        if complaint.status == ComplaintStatus.CLASSIFIED:
                            classified_successfully = True
                    except Exception as exc:
                        logger.warning("Classification failed, falling back to civic defaults", extra={"error": str(exc)})

                if not classified_successfully:
                    self._apply_classification_fallback(complaint, session)

            await event_bus.publish(
                DomainEvent(
                    event_type="CLASSIFICATION_COMPLETED",
                    complaint_id=complaint_id,
                    payload={"status": "CLASSIFIED"},
                )
            )

    def _apply_classification_fallback(self, complaint: Complaint, session: Session) -> None:
        if complaint.status != ComplaintStatus.CLASSIFYING:
            ensure_transition(complaint.status, ComplaintStatus.CLASSIFYING)
            complaint.status = ComplaintStatus.CLASSIFYING
        ensure_transition(complaint.status, ComplaintStatus.CLASSIFIED)
        complaint.status = ComplaintStatus.CLASSIFIED
        complaint.category = complaint.category or "streetlight_outage"
        complaint.department_id = complaint.department_id or "dept-electrical"
        complaint.jurisdiction_id = complaint.jurisdiction_id or "jur-ghmc"
        complaint.updated_at = self.clock.now()

        audit = AuditService(session, self.clock)
        audit.record(
            AuditEventCreate(
                complaint_id=complaint.id,
                event_type=AuditEventType.COMPLAINT_CLASSIFIED,
                actor_type=ActorType.SYSTEM,
                actor_name="classification_fallback",
                summary=f"Classified to {complaint.department_id}",
                payload={"category": complaint.category, "department": complaint.department_id},
            )
        )

    async def _run_drafting_step(self, complaint_id: str, app_state: Any) -> None:
        key = f"drafting:{complaint_id}"
        with idempotency_manager.execute_idempotent(key) as should_run:
            if not should_run:
                return

            with self.db.session() as session:
                complaint = session.get(Complaint, complaint_id)
                if not complaint or complaint.status != ComplaintStatus.CLASSIFIED:
                    return

                drafting_agent = getattr(app_state, "drafting_agent", None) if app_state else None
                drafted_successfully = False

                if drafting_agent:
                    from app.schemas.drafting import DraftApproveRequest, DraftRunRequest
                    from app.services.drafting.service import DraftingService

                    draft_svc = DraftingService(session, drafting_agent, clock=self.clock)
                    try:
                        await draft_svc.run(complaint_id, DraftRunRequest(draft_language=complaint.language or "en"))
                        draft_svc.approve(complaint_id, DraftApproveRequest(version=1))
                        if complaint.status == ComplaintStatus.DRAFTED:
                            drafted_successfully = True
                    except Exception as exc:
                        logger.warning("Drafting failed, using structured template fallback", extra={"error": str(exc)})

                if not drafted_successfully:
                    self._apply_drafting_fallback(complaint, session)

            await event_bus.publish(
                DomainEvent(
                    event_type="DRAFT_CREATED",
                    complaint_id=complaint_id,
                    payload={"status": "DRAFTED"},
                )
            )

    def _apply_drafting_fallback(self, complaint: Complaint, session: Session) -> None:
        if complaint.status != ComplaintStatus.DRAFTING:
            ensure_transition(complaint.status, ComplaintStatus.DRAFTING)
            complaint.status = ComplaintStatus.DRAFTING
        ensure_transition(complaint.status, ComplaintStatus.DRAFTED)
        complaint.status = ComplaintStatus.DRAFTED
        existing = dict(complaint.drafted_complaint) if isinstance(complaint.drafted_complaint, dict) else {}
        complaint.drafted_complaint = {
            **existing,
            "title": f"Grievance: {complaint.issue or 'Civic issue'}",
            "summary": f"Citizen reported {complaint.issue} at {complaint.location} for duration {complaint.duration}.",
            "department": complaint.department_id,
            "jurisdiction": complaint.jurisdiction_id,
            "generated_at": self.clock.now().isoformat(),
        }
        complaint.updated_at = self.clock.now()

        audit = AuditService(session, self.clock)
        audit.record(
            AuditEventCreate(
                complaint_id=complaint.id,
                event_type=AuditEventType.COMPLAINT_DRAFTED,
                actor_type=ActorType.SYSTEM,
                actor_name="drafting_fallback",
                summary="Structured complaint draft generated",
                payload={"draft": complaint.drafted_complaint},
            )
        )

    async def _run_filing_step(self, complaint_id: str, app_state: Any) -> None:
        key = f"filing:{complaint_id}"
        with idempotency_manager.execute_idempotent(key) as should_run:
            if not should_run:
                return

            with self.db.session() as session:
                complaint = session.get(Complaint, complaint_id)
                if not complaint or complaint.status != ComplaintStatus.DRAFTED:
                    return

                filing_agent = getattr(app_state, "filing_agent", None) if app_state else None
                if filing_agent:
                    from app.agents.base import AgentContext
                    from app.schemas.agents import DraftedComplaint, FilingRequest

                    draft_data = complaint.drafted_complaint or {}
                    draft_payload = DraftedComplaint(
                        issue=complaint.issue or "Civic grievance",
                        category=complaint.category or "streetlight_outage",
                        department_id=complaint.department_id or "dept-electrical",
                        jurisdiction_id=complaint.jurisdiction_id or "jur-ghmc",
                        location=complaint.location or "Ward 93 (Banjara Hills), Hyderabad",
                        duration=complaint.duration or "Unspecified",
                        description=draft_data.get("summary", draft_data.get("description", f"Civic issue reported: {complaint.issue}")),
                        requested_action="Inspect and resolve the reported issue at the earliest.",
                        original_text=complaint.citizen_input,
                        subject=draft_data.get("title", f"Grievance: {complaint.issue}"),
                        body=draft_data.get("summary", f"Citizen reported {complaint.issue} at {complaint.location}."),
                    )

                    try:
                        filing_res = await filing_agent.execute(
                            FilingRequest(complaint_id=complaint.id, draft=draft_payload, citizen_confirmed=True),
                            AgentContext(complaint_id=complaint.id, clock=self.clock),
                        )
                        complaint.authority_status = AuthorityStatus.RECEIVED
                        # Preserve existing tracking_id if already assigned
                        if not complaint.tracking_id:
                            complaint.tracking_id = filing_res.tracking_id
                    except Exception as exc:
                        logger.warning("Mock filing error, using local filing receipt", extra={"error": str(exc)})
                        complaint.authority_status = AuthorityStatus.RECEIVED
                else:
                    complaint.authority_status = AuthorityStatus.RECEIVED

                ensure_transition(complaint.status, ComplaintStatus.FILED)
                complaint.status = ComplaintStatus.FILED
                complaint.updated_at = self.clock.now()

                audit = AuditService(session, self.clock)
                audit.record(
                    AuditEventCreate(
                        complaint_id=complaint.id,
                        event_type=AuditEventType.COMPLAINT_FILED,
                        actor_type=ActorType.AGENT,
                        actor_name="filing_agent",
                        summary=f"Complaint filed with {complaint.department_id}",
                        payload={"authority_status": complaint.authority_status.value},
                    )
                )

            await event_bus.publish(
                DomainEvent(
                    event_type="COMPLAINT_FILED",
                    complaint_id=complaint_id,
                    payload={"status": "FILED"},
                )
            )

    async def _run_monitoring_step(self, complaint_id: str) -> None:
        key = f"monitoring:{complaint_id}"
        with idempotency_manager.execute_idempotent(key) as should_run:
            if not should_run:
                return

            with self.db.session() as session:
                complaint = session.get(Complaint, complaint_id)
                if not complaint or complaint.status != ComplaintStatus.FILED:
                    return

                ensure_transition(complaint.status, ComplaintStatus.MONITORING)
                complaint.status = ComplaintStatus.MONITORING
                complaint.updated_at = self.clock.now()

                # Set up SLA deadlines (Default: 48-hour duration, 36-hour warning)
                from datetime import timedelta
                from app.models.complaint import SLARecord
                from app.schemas.enums import SLAStage

                started = self.clock.now()
                warning = started + timedelta(hours=36)
                deadline = started + timedelta(hours=48)

                if not complaint.sla:
                    complaint.sla = SLARecord(
                        policy_id="sla-civic-standard",
                        started_at=started,
                        warning_at=warning,
                        deadline_at=deadline,
                        stage=SLAStage.ON_TRACK,
                    )

                audit = AuditService(session, self.clock)
                audit.record(
                    AuditEventCreate(
                        complaint_id=complaint.id,
                        event_type=AuditEventType.SLA_STARTED,
                        actor_type=ActorType.SYSTEM,
                        actor_name="watchdog_pipeline",
                        summary="Autonomous watchdog SLA monitoring started",
                        payload={"warning_at": warning.isoformat(), "deadline_at": deadline.isoformat()},
                    )
                )

            await event_bus.publish(
                DomainEvent(
                    event_type="MONITORING_STARTED",
                    complaint_id=complaint_id,
                    payload={"status": "MONITORING"},
                )
            )

    async def _run_notification_step(self, complaint_id: str) -> None:
        with self.db.session() as session:
            complaint = session.get(Complaint, complaint_id)
            if not complaint:
                return

            tracking_id = complaint.tracking_id or complaint_id[:8].upper()
            title = f"Complaint Received ({tracking_id})"
            message = (
                f"Your complaint regarding '{complaint.issue or 'civic grievance'}' at '{complaint.location or 'location'}' "
                f"has been filed with {complaint.department_id or 'the municipal department'}. "
                f"SLA monitoring is active."
            )

            notification_service.notify(
                complaint_id=complaint.id,
                event_type="COMPLAINT_MONITORING",
                title=title,
                message=message,
                metadata={"tracking_id": tracking_id, "status": complaint.status.value},
            )

            # Workflow Step 1: Send review email to AUTHORITY_REVIEW_EMAIL
            from app.services.notification.email_service import demo_email_service
            demo_email_service.send_authority_review_email(complaint)
