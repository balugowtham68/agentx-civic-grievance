"""Agent 5 - Autonomous Watchdog (behaviour: Phases 7-8). Core differentiator.

On every scheduler tick, for each active complaint: poll mock API status, track
the SLA, detect approaching deadline and breach, evaluate configured escalation
policies, escalate to a human authority when a policy matches, and record why.

ACKNOWLEDGED != RESOLVED: only the policy's terminal_states (default RESOLVED,
CLOSED) stop the SLA or block escalation.
"""

from __future__ import annotations
from datetime import timedelta

from app.agents.base import AgentContext, BaseAgent
from app.core.errors import NotImplementedYetError
from app.repositories import ReferenceRepository
from app.schemas.agents import (
    WatchdogEvaluationRequest,
    WatchdogEvaluationResult,
    RuleEvaluation,
    ConditionResult,
    EscalationResult,
)
from app.schemas.enums import AgentName, AuthorityStatus, ComplaintStatus, SLAStage, EscalationState
from app.schemas.mock_gov import MockEscalationRequest
from app.services.external import EscalationNotifier, MockGovernmentGrievanceAPI


class WatchdogAgent(BaseAgent[WatchdogEvaluationRequest, WatchdogEvaluationResult]):
    name = AgentName.WATCHDOG
    description = "Monitors filed complaints, tracks SLA and escalates by configured policy"
    phase = 7
    input_model = WatchdogEvaluationRequest
    output_model = WatchdogEvaluationResult

    def __init__(
        self,
        mock_gov: MockGovernmentGrievanceAPI,
        reference: ReferenceRepository,
        notifier: EscalationNotifier | None = None,
    ) -> None:
        self.mock_gov = mock_gov
        self.reference = reference
        self.notifier = notifier

    async def _run(
        self, payload: WatchdogEvaluationRequest, context: AgentContext
    ) -> WatchdogEvaluationResult:
        # 1. Fetch current status from Mock Gov API
        mock_status = await self.mock_gov.get_status(payload.tracking_id)
        
        reasons = []
        rule_evals = []
        new_status = payload.current_status
        authority_status = mock_status.status
        sla_stage = SLAStage.NOT_STARTED
        warning_raised = False
        escalation_result = None
        
        # 2. Check if terminal state reached
        policy = self.reference.escalation_policy_for_category(payload.category)
        terminal_states = policy.terminal_states if policy else [AuthorityStatus.RESOLVED, AuthorityStatus.CLOSED]
        
        if authority_status in terminal_states:
            sla_stage = SLAStage.STOPPED
            if new_status not in [ComplaintStatus.RESOLVED, ComplaintStatus.CLOSED]:
                new_status = ComplaintStatus.RESOLVED
        elif payload.sla:
            # 3. Determine SLA Stage
            if payload.evaluated_at >= payload.sla.deadline_at:
                sla_stage = SLAStage.BREACHED
                if new_status not in [ComplaintStatus.BREACHED, ComplaintStatus.ESCALATED]:
                    new_status = ComplaintStatus.BREACHED
            elif payload.evaluated_at >= payload.sla.warning_at:
                sla_stage = SLAStage.APPROACHING
                if new_status == ComplaintStatus.MONITORING:
                    new_status = ComplaintStatus.WARNING
                    warning_raised = True
            else:
                sla_stage = SLAStage.ON_TRACK
        
        # 4. Evaluate Escalation Policy
        if policy and policy.enabled and authority_status not in terminal_states:
            trigger = policy.trigger
            
            # Check conditions
            cond_status = ConditionResult(
                name="status_condition",
                expected=str(trigger.source_statuses),
                actual=str(new_status),
                passed=new_status in trigger.source_statuses
            )
            
            # Since trigger.sla_condition is not easily accessible via generic triggers sometimes, we explicitly check SLAStage
            cond_sla = ConditionResult(
                name="sla_condition",
                expected=str(SLAStage.BREACHED),
                actual=str(sla_stage),
                passed=(sla_stage == SLAStage.BREACHED)
            )
            
            rule_eval = RuleEvaluation(
                policy_id=policy.id,
                level=0, # Calculated below
                matched=cond_status.passed and cond_sla.passed,
                conditions=[cond_status, cond_sla],
                evaluated_at=payload.evaluated_at
            )
            
            if rule_eval.matched:
                # Find the next level to escalate to
                current_level = 0
                last_escalation_time = None
                
                if payload.escalations:
                    latest = max(payload.escalations, key=lambda e: e.level)
                    current_level = latest.level
                    last_escalation_time = latest.created_at
                
                next_level_obj = next((lvl for lvl in policy.levels if lvl.level == current_level + 1), None)
                
                if next_level_obj:
                    rule_eval.level = next_level_obj.level
                    can_escalate = True
                    
                    if last_escalation_time and next_level_obj.after_hours > 0:
                        required_time = last_escalation_time + timedelta(hours=next_level_obj.after_hours)
                        if payload.evaluated_at < required_time:
                            can_escalate = False
                            reasons.append(f"Waiting for Level {next_level_obj.level} delay ({next_level_obj.after_hours}h)")
                            
                    if can_escalate:
                        # Perform Escalation
                        esc_req = MockEscalationRequest(
                            tracking_id=payload.tracking_id,
                            level=next_level_obj.level,
                            target_authority_id=next_level_obj.target_authority_id,
                            reason=f"SLA breached and policy {policy.id} condition met",
                            idempotency_key=f"esc-{payload.complaint_id}-{next_level_obj.level}"
                        )
                        receipt = await self.mock_gov.escalate(esc_req)
                        
                        escalation_result = EscalationResult(
                            complaint_id=payload.complaint_id,
                            policy_id=policy.id,
                            level=next_level_obj.level,
                            target_authority_id=next_level_obj.target_authority_id,
                            state=EscalationState.ESCALATED,
                            reason=esc_req.reason,
                            created=receipt.created
                        )
                        new_status = ComplaintStatus.ESCALATED
                        reasons.append(f"Escalated to Level {next_level_obj.level} ({next_level_obj.target_authority_id})")
                        
            rule_evals.append(rule_eval)
            
        return WatchdogEvaluationResult(
            complaint_id=payload.complaint_id,
            evaluated_at=payload.evaluated_at,
            previous_status=payload.current_status,
            new_status=new_status,
            authority_status=authority_status,
            sla_stage=sla_stage,
            warning_raised=warning_raised,
            rule_evaluations=rule_evals,
            escalation=escalation_result,
            reasons=reasons
        )
