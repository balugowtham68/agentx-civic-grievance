"""Configured civic reference data: departments, jurisdictions, SLA policies,
escalation policies and authorities.

These are loaded from `knowledge_base/` JSON files (demo configuration for the
hackathon, clearly labelled as such). Decisions made by agents must reference
IDs defined here; nothing is invented.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, model_validator

from app.schemas.enums import AuthorityStatus, ComplaintStatus, SLAStage

ID_PATTERN = r"^[A-Z0-9][A-Z0-9_-]{1,63}$"


class Department(BaseModel):
    id: str = Field(pattern=ID_PATTERN)
    name: str
    description: str
    categories: list[str] = Field(min_length=1)


class Jurisdiction(BaseModel):
    id: str = Field(pattern=ID_PATTERN)
    name: str
    type: str = "ward"
    localities: list[str] = Field(default_factory=list)
    landmarks: list[str] = Field(default_factory=list)


class Authority(BaseModel):
    """A human authority an escalation can be handed to."""

    id: str = Field(pattern=ID_PATTERN)
    title: str
    jurisdiction_id: str | None = None
    department_id: str | None = None


class SLAPolicy(BaseModel):
    id: str = Field(pattern=ID_PATTERN)
    category: str
    department_id: str
    duration_hours: int = Field(gt=0)
    warning_after_hours: int = Field(gt=0)

    @model_validator(mode="after")
    def _warning_before_deadline(self) -> "SLAPolicy":
        if self.warning_after_hours >= self.duration_hours:
            raise ValueError("warning_after_hours must be less than duration_hours")
        return self


class EscalationTrigger(BaseModel):
    """When a policy fires. All conditions must hold."""

    source_statuses: list[ComplaintStatus] = Field(
        default_factory=lambda: [ComplaintStatus.BREACHED]
    )
    sla_condition: SLAStage = SLAStage.BREACHED


class EscalationLevel(BaseModel):
    level: int = Field(ge=1)
    target_authority_id: str
    # Extra time after the previous level before this level may fire (0 = immediately).
    after_hours: int = Field(default=0, ge=0)


def _default_terminal_states() -> list[AuthorityStatus]:
    # ACKNOWLEDGED is deliberately absent: ACKNOWLEDGED != RESOLVED.
    return [AuthorityStatus.RESOLVED, AuthorityStatus.CLOSED]


class EscalationPolicy(BaseModel):
    id: str = Field(pattern=ID_PATTERN)
    name: str
    enabled: bool = True
    categories: list[str] = Field(min_length=1)
    trigger: EscalationTrigger = Field(default_factory=EscalationTrigger)
    levels: list[EscalationLevel] = Field(min_length=1)
    # Authority statuses that stop the SLA and block escalation.
    terminal_states: list[AuthorityStatus] = Field(default_factory=_default_terminal_states)

    @model_validator(mode="after")
    def _levels_are_sequential(self) -> "EscalationPolicy":
        numbers = [lvl.level for lvl in self.levels]
        if numbers != list(range(1, len(numbers) + 1)):
            raise ValueError("escalation levels must be numbered 1..n in order")
        if not self.terminal_states:
            raise ValueError("terminal_states cannot be empty")
        return self


class ReferenceData(BaseModel):
    """Everything loaded from knowledge_base/ config files, cross-validated."""

    departments: list[Department]
    jurisdictions: list[Jurisdiction]
    authorities: list[Authority]
    sla_policies: list[SLAPolicy]
    escalation_policies: list[EscalationPolicy]

    @model_validator(mode="after")
    def _references_exist(self) -> "ReferenceData":
        dept_ids = {d.id for d in self.departments}
        jur_ids = {j.id for j in self.jurisdictions}
        auth_ids = {a.id for a in self.authorities}
        problems: list[str] = []
        for policy in self.sla_policies:
            if policy.department_id not in dept_ids:
                problems.append(f"SLA policy {policy.id}: unknown department {policy.department_id}")
        for auth in self.authorities:
            if auth.jurisdiction_id and auth.jurisdiction_id not in jur_ids:
                problems.append(f"Authority {auth.id}: unknown jurisdiction {auth.jurisdiction_id}")
            if auth.department_id and auth.department_id not in dept_ids:
                problems.append(f"Authority {auth.id}: unknown department {auth.department_id}")
        for esc in self.escalation_policies:
            for lvl in esc.levels:
                if lvl.target_authority_id not in auth_ids:
                    problems.append(
                        f"Escalation policy {esc.id}: unknown authority {lvl.target_authority_id}"
                    )
        if problems:
            raise ValueError("; ".join(problems))
        return self
