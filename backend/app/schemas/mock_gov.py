"""Contracts for the Mock Government Grievance API (hackathon simulation only).

SPANDAN AI never talks to a real government portal. Every response from the mock
carries `simulation: true`.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.agents import DraftedComplaint
from app.schemas.enums import AuthorityStatus


class MockGrievanceSubmission(BaseModel):
    complaint_id: str
    complaint: DraftedComplaint


class MockGrievanceReceipt(BaseModel):
    tracking_id: str = Field(pattern=r"^CIV-\d{4}-\d{4,}$")
    received_at: datetime
    status: AuthorityStatus = AuthorityStatus.RECEIVED
    simulation: Literal[True] = True


class MockAuthorityUpdate(BaseModel):
    status: AuthorityStatus
    actor: str
    note: str | None = None
    at: datetime


class MockGrievanceStatus(BaseModel):
    tracking_id: str
    status: AuthorityStatus
    updates: list[MockAuthorityUpdate] = Field(default_factory=list)
    simulation: Literal[True] = True


class MockEscalationRequest(BaseModel):
    tracking_id: str
    level: int = Field(ge=1)
    target_authority_id: str
    reason: str
    idempotency_key: str


class MockEscalationReceipt(BaseModel):
    escalation_reference: str
    tracking_id: str
    level: int
    target_authority_id: str
    created: bool
    simulation: Literal[True] = True
