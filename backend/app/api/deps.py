"""FastAPI dependencies. Routes get services from here, never sessions or SQL."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.database import Database
from app.repositories import ReferenceRepository
from app.services.audit_service import AuditService
from app.services.complaint_service import ComplaintService


def get_app_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_database(request: Request) -> Database:
    return request.app.state.db


def get_session(db: Annotated[Database, Depends(get_database)]) -> Iterator[Session]:
    with db.session() as session:
        yield session


def get_reference(request: Request) -> ReferenceRepository:
    return request.app.state.reference


def get_complaint_service(session: Annotated[Session, Depends(get_session)]) -> ComplaintService:
    return ComplaintService(session)


def get_audit_service(session: Annotated[Session, Depends(get_session)]) -> AuditService:
    return AuditService(session)


SettingsDep = Annotated[Settings, Depends(get_app_settings)]
DatabaseDep = Annotated[Database, Depends(get_database)]
ReferenceDep = Annotated[ReferenceRepository, Depends(get_reference)]
ComplaintServiceDep = Annotated[ComplaintService, Depends(get_complaint_service)]
AuditServiceDep = Annotated[AuditService, Depends(get_audit_service)]
