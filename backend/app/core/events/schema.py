"""Domain event schema for SPANDAN AI event-driven architecture."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class DomainEvent(BaseModel):
    """Immutable domain event record."""

    event_id: str = Field(default_factory=lambda: str(uuid4()))
    event_type: str
    complaint_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    payload: dict[str, Any] = Field(default_factory=dict)
    correlation_id: str = Field(default_factory=lambda: str(uuid4()))
    schema_version: str = "1.0"

    class Config:
        frozen = True
