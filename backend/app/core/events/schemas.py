"""Domain event and background job schemas for SPANDAN AI."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class EventType(StrEnum):
    COMPLAINT_CREATED = "COMPLAINT_CREATED"
    LANGUAGE_DETECTED = "LANGUAGE_DETECTED"
    INTAKE_COMPLETED = "INTAKE_COMPLETED"
    LOCATION_RESOLVED = "LOCATION_RESOLVED"
    CLASSIFICATION_COMPLETED = "CLASSIFICATION_COMPLETED"
    RAG_CONTEXT_RETRIEVED = "RAG_CONTEXT_RETRIEVED"
    DRAFT_CREATED = "DRAFT_CREATED"
    COMPLAINT_FILED = "COMPLAINT_FILED"
    MONITORING_STARTED = "MONITORING_STARTED"
    SLA_WARNING = "SLA_WARNING"
    SLA_BREACHED = "SLA_BREACHED"
    ESCALATION_TRIGGERED = "ESCALATION_TRIGGERED"
    COMPLAINT_RESOLVED = "COMPLAINT_RESOLVED"
    COMPLAINT_CLOSED = "COMPLAINT_CLOSED"
    NOTIFICATION_SENT = "NOTIFICATION_SENT"


class DomainEvent(BaseModel):
    """Immutable domain event recording a state or workflow change."""

    event_id: str = Field(default_factory=lambda: str(uuid4()))
    event_type: EventType
    complaint_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    payload: dict[str, Any] = Field(default_factory=dict)
    correlation_id: str | None = None
    schema_version: int = 1


class JobStatus(StrEnum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    DEAD_LETTER = "DEAD_LETTER"


class Job(BaseModel):
    """A background asynchronous work item."""

    job_id: str = Field(default_factory=lambda: str(uuid4()))
    job_type: str
    complaint_id: str
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    status: JobStatus = JobStatus.PENDING
    retry_count: int = 0
    max_retries: int = 3
    error_message: str | None = None
    idempotency_key: str | None = None
