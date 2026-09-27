"""Orchestrator for the Watchdog Agent."""

from __future__ import annotations

import asyncio
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.agents.base import AgentContext
from app.agents.watchdog.agent import WatchdogAgent
from app.core.clock import Clock, get_clock
from app.models import Complaint, SLARecord, EscalationRecord
from app.repositories import ComplaintRepository, EscalationRepository
from app.schemas.agents import WatchdogEvaluationRequest
from app.schemas.audit import AuditEventCreate
from app.schemas.complaint import SLAStateRead, EscalationRead
from app.schemas.enums import ActorType, AuditEventType, ComplaintStatus, SLAStage, EscalationState
from app.services.audit_service import AuditService
from app.core.logging import get_logger

logger = get_logger(__name__)


class WatchdogService:
    def __init__(self, session: Session, agent: WatchdogAgent, clock: Clock | None = None) -> None:
        self.session = session
        self.agent = agent
        self.clock = clock or get_clock()
        self.repo = ComplaintRepository(session)
        self.escalation_repo = EscalationRepository(session)
        self.audit = AuditService(session, self.clock)

    async def run_cycle(self) -> dict[str, int]:
        """Executes one full watchdog cycle. Returns summary statistics."""
        now = self.clock.now()
        
        # Load active complaints
        # We only monitor complaints that are FILED, MONITORING, WARNING, BREACHED, ESCALATED
        active_statuses = {
            ComplaintStatus.FILED,
            ComplaintStatus.MONITORING,
            ComplaintStatus.WARNING,
            ComplaintStatus.BREACHED,
            ComplaintStatus.ESCALATED,
        }
        
        complaints, _ = self.repo.list(statuses=active_statuses, limit=1000)
        
        stats = {
            "checked": len(complaints),
            "warnings": 0,
            "breaches": 0,
            "escalations": 0,
            "errors": 0
        }
        
        for complaint in complaints:
            if not complaint.tracking_id:
                continue
                
            try:
                # Prepare Request
                sla_read = SLAStateRead.model_validate(complaint.sla) if complaint.sla else None
                escalations = [EscalationRead.model_validate(e) for e in complaint.escalations]
                
                req = WatchdogEvaluationRequest(
                    complaint_id=complaint.id,
                    tracking_id=complaint.tracking_id,
                    category=complaint.category,
                    department_id=complaint.department_id,
                    jurisdiction_id=complaint.jurisdiction_id,
                    current_status=complaint.status,
                    authority_status=complaint.authority_status,
                    escalation_state=complaint.escalation_state,
                    sla=sla_read,
                    escalations=escalations,
                    evaluated_at=now
                )
                
                # Run Agent
                result = await self.agent.execute(req, AgentContext(complaint.id, self.clock))
                
                # Apply changes
                changed = False
                
                if complaint.authority_status != result.authority_status:
                    complaint.authority_status = result.authority_status
                    changed = True
                    self.audit.record(
                        AuditEventCreate(
                            complaint_id=complaint.id,
                            event_type=AuditEventType.AUTHORITY_UPDATE_DETECTED,
                            actor_type=ActorType.SYSTEM,
                            actor_name="mock_government",
                            summary=f"Authority status updated to {result.authority_status.value}",
                            payload={"authority_status": result.authority_status.value}
                        )
                    )
                    
                if complaint.sla and complaint.sla.stage != result.sla_stage:
                    complaint.sla.stage = result.sla_stage
                    if result.sla_stage == SLAStage.STOPPED:
                        complaint.sla.stopped_at = now
                        complaint.sla.stop_reason = "Terminal state reached"
                    changed = True
                    
                if result.warning_raised:
                    stats["warnings"] += 1
                    self.audit.record(
                        AuditEventCreate(
                            complaint_id=complaint.id,
                            event_type=AuditEventType.SLA_WARNING,
                            actor_type=ActorType.SYSTEM,
                            actor_name="watchdog",
                            summary="SLA warning threshold reached"
                        )
                    )
                    
                if complaint.status != result.new_status:
                    if result.new_status == ComplaintStatus.BREACHED:
                        stats["breaches"] += 1
                        self.audit.record(
                            AuditEventCreate(
                                complaint_id=complaint.id,
                                event_type=AuditEventType.SLA_BREACHED,
                                actor_type=ActorType.SYSTEM,
                                actor_name="watchdog",
                                summary="SLA deadline breached"
                            )
                        )
                    elif result.new_status == ComplaintStatus.RESOLVED:
                        self.audit.record(
                            AuditEventCreate(
                                complaint_id=complaint.id,
                                event_type=AuditEventType.COMPLAINT_RESOLVED,
                                actor_type=ActorType.AUTHORITY,
                                actor_name="mock_government",
                                summary="Complaint resolved by authority"
                            )
                        )
                    complaint.status = result.new_status
                    changed = True
                    
                if result.escalation:
                    stats["escalations"] += 1
                    esc = result.escalation
                    
                    if esc.created:
                        esc_record = EscalationRecord(
                            complaint_id=complaint.id,
                            level=esc.level,
                            policy_id=esc.policy_id,
                            target_authority_id=esc.target_authority_id,
                            state=esc.state,
                            reason=esc.reason,
                            mock_reference=f"ESC-{now.timestamp()}",
                            created_at=now,
                            updated_at=now
                        )
                        self.escalation_repo.add(esc_record)
                        
                        self.audit.record(
                            AuditEventCreate(
                                complaint_id=complaint.id,
                                event_type=AuditEventType.ESCALATION_TRIGGERED,
                                actor_type=ActorType.SYSTEM,
                                actor_name="watchdog",
                                summary=f"Escalated to Level {esc.level} ({esc.target_authority_id})",
                                payload={"reason": esc.reason, "level": esc.level}
                            )
                        )
                    changed = True
                    
                if changed:
                    complaint.updated_at = now
                    
            except Exception as exc:
                logger.exception("Watchdog failed for complaint", extra={"complaint_id": complaint.id})
                stats["errors"] += 1
                
        # Commit all changes at the end of the cycle
        self.session.commit()
        return stats
