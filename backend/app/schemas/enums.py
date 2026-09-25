"""Domain enums shared by the database, API contracts and agents.

StrEnum values are what is stored in the database and sent over the API, so
renaming a value is a breaking contract change (see docs/architecture.md).
"""

from __future__ import annotations

from enum import StrEnum


class ComplaintStatus(StrEnum):
    """Lifecycle status of a complaint inside AGENT X.

    UNDERSTAND -> CLASSIFY -> DRAFT -> FILE -> MONITOR -> DECIDE -> ESCALATE -> EXPLAIN
    Allowed moves are defined in app/core/state_machine.py.
    """

    CREATED = "CREATED"
    NEEDS_INFO = "NEEDS_INFO"  # a required fact is missing; citizen is asked
    UNDERSTOOD = "UNDERSTOOD"
    CLASSIFIED = "CLASSIFIED"
    NEEDS_REVIEW = "NEEDS_REVIEW"  # classification not grounded in the knowledge base
    DRAFTED = "DRAFTED"
    FILED = "FILED"
    FILING_FAILED = "FILING_FAILED"
    MONITORING = "MONITORING"
    WARNING = "WARNING"  # SLA approaching
    BREACHED = "BREACHED"  # SLA deadline passed
    ESCALATED = "ESCALATED"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"


class AuthorityStatus(StrEnum):
    """What the (mock) government side reports about the complaint.

    ACKNOWLEDGED != RESOLVED: acknowledgement is recorded and audited but, by
    default, does not stop the SLA or escalation. See EscalationPolicy.terminal_states.
    """

    NONE = "NONE"
    RECEIVED = "RECEIVED"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"


class SLAStage(StrEnum):
    NOT_STARTED = "NOT_STARTED"
    ON_TRACK = "ON_TRACK"
    APPROACHING = "APPROACHING"
    BREACHED = "BREACHED"
    STOPPED = "STOPPED"  # a configured terminal state was reached


class EscalationState(StrEnum):
    NONE = "NONE"
    ESCALATED = "ESCALATED"  # handed to a human authority, awaiting response
    ACKNOWLEDGED = "ACKNOWLEDGED"  # authority acknowledged the escalation
    CLOSED = "CLOSED"  # complaint resolved/closed after escalation


class InputChannel(StrEnum):
    TEXT = "text"
    VOICE = "voice"


class AgentName(StrEnum):
    INTAKE = "intake"
    CLASSIFICATION = "classification"
    DRAFTING = "drafting"
    FILING = "filing"
    WATCHDOG = "watchdog"


class ActorType(StrEnum):
    AGENT = "agent"
    CITIZEN = "citizen"
    AUTHORITY = "authority"
    SYSTEM = "system"


class AuditEventType(StrEnum):
    COMPLAINT_CREATED = "complaint.created"
    COMPLAINT_TRANSCRIBED = "complaint.transcribed"
    COMPLAINT_TRANSLATED = "complaint.translated"
    COMPLAINT_UNDERSTOOD = "complaint.understood"
    COMPLAINT_INFO_REQUESTED = "complaint.info_requested"
    KNOWLEDGE_RETRIEVED = "knowledge.retrieved"
    COMPLAINT_CLASSIFIED = "complaint.classified"
    COMPLAINT_NEEDS_REVIEW = "complaint.needs_review"
    COMPLAINT_DRAFTED = "complaint.drafted"
    COMPLAINT_DRAFT_CORRECTED = "complaint.draft_corrected"
    COMPLAINT_CONFIRMED = "complaint.confirmed"
    COMPLAINT_FILED = "complaint.filed"
    COMPLAINT_FILING_FAILED = "complaint.filing_failed"
    SLA_STARTED = "sla.started"
    MONITORING_CHECKED = "monitoring.checked"
    AUTHORITY_UPDATE_DETECTED = "authority.update_detected"
    SLA_WARNING = "sla.warning"
    SLA_BREACHED = "sla.breached"
    SLA_STOPPED = "sla.stopped"
    ESCALATION_RULE_EVALUATED = "escalation.rule_evaluated"
    ESCALATION_TRIGGERED = "escalation.triggered"
    COMPLAINT_RESOLVED = "complaint.resolved"
    COMPLAINT_CLOSED = "complaint.closed"
