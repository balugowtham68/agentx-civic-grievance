"""Domain enums shared by the database, API contracts and agents.

StrEnum values are what is stored in the database and sent over the API, so
renaming a value is a breaking contract change (see docs/architecture.md).
"""

from __future__ import annotations

from enum import StrEnum


class ComplaintStatus(StrEnum):
    """Lifecycle status of a complaint inside SPANDAN AI.

    UNDERSTAND -> CLASSIFY -> DRAFT -> FILE -> MONITOR -> DECIDE -> ESCALATE -> EXPLAIN
    Allowed moves are defined in app/core/state_machine.py.
    """

    CREATED = "CREATED"
    NEEDS_INFO = "NEEDS_INFO"  # a required fact is missing; citizen is asked
    UNDERSTANDING = "UNDERSTANDING"  # intake complete; waiting for the citizen to confirm
    UNDERSTOOD = "UNDERSTOOD"  # citizen confirmed what was understood (ready for Phase 3)
    CLASSIFYING = "CLASSIFYING"  # Phase 3 classification is running
    CLASSIFIED = "CLASSIFIED"  # category, department and jurisdiction grounded in the knowledge base
    NEEDS_REVIEW = "NEEDS_REVIEW"  # classification not grounded in the knowledge base (UNSUPPORTED_CLASSIFICATION)
    DRAFTING = "DRAFTING"  # Phase 4: a draft exists and awaits the citizen's review
    DRAFTED = "DRAFTED"  # the citizen approved a draft version (ready for Phase 5 filing)
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
    # Citizen intake (Phase 2)
    INTAKE_RECEIVED = "intake.received"
    INTAKE_LANGUAGE_DETECTED = "intake.language_detected"
    INTAKE_TRANSLATION_FAILED = "intake.translation_failed"
    INTAKE_FACTS_EXTRACTED = "intake.facts_extracted"
    INTAKE_FACTS_REJECTED = "intake.facts_rejected"
    INTAKE_MISSING_INFO_DETECTED = "intake.missing_info_detected"
    INTAKE_CLARIFICATION_ANSWERED = "intake.clarification_answered"
    INTAKE_CORRECTED = "intake.corrected"
    INTAKE_CONFIRMED = "intake.confirmed"
    INTAKE_FAILED = "intake.failed"
    # Classification & Reasoning (Phase 3)
    CLASSIFICATION_STARTED = "classification.started"
    KNOWLEDGE_RETRIEVED = "knowledge.retrieved"
    CLASSIFICATION_CANDIDATES_GENERATED = "classification.candidates"
    CLASSIFICATION_RULE_MATCHED = "classification.rule_matched"
    CLASSIFICATION_NEEDS_INFO = "classification.needs_info"
    CLASSIFICATION_AMBIGUOUS = "classification.ambiguous"
    CLASSIFICATION_COMPLETED = "classification.completed"
    CLASSIFICATION_REJECTED = "classification.rejected"
    CLASSIFICATION_ANSWERED = "classification.answered"
    COMPLAINT_CLASSIFIED = "complaint.classified"
    COMPLAINT_NEEDS_REVIEW = "complaint.needs_review"
    # Complaint drafting (Phase 4)
    DRAFTING_STARTED = "drafting.started"
    DRAFTING_SOURCE_LOADED = "drafting.source_loaded"
    DRAFTING_GENERATED = "drafting.generated"
    DRAFTING_VALIDATION_PASSED = "drafting.validation_passed"
    DRAFTING_VALIDATION_FAILED = "drafting.validation_failed"
    DRAFTING_EDITED = "drafting.edited"
    DRAFTING_VERSION_CREATED = "drafting.version_created"
    DRAFTING_FALLBACK = "drafting.fallback"
    DRAFTING_APPROVED = "drafting.approved"
    DRAFTING_APPROVAL_WITHDRAWN = "drafting.approval_withdrawn"
    DRAFTING_COMPLETED = "drafting.completed"
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
