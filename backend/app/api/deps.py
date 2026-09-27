"""FastAPI dependencies. Routes get services from here, never sessions or SQL."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Annotated, Any

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.database import Database
from app.repositories import ReferenceRepository
from app.services.audit_service import AuditService
from app.services.classification.service import ClassificationService
from app.services.complaint_service import ComplaintService
from app.services.drafting.service import DraftingService
from app.services.intake.service import IntakeService


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


def get_intake_service(
    request: Request, session: Annotated[Session, Depends(get_session)]
) -> IntakeService:
    state = request.app.state
    return IntakeService(session, state.intake_agent, state.languages, state.settings)


def get_classification_service(
    request: Request, session: Annotated[Session, Depends(get_session)]
) -> ClassificationService:
    state = request.app.state
    return ClassificationService(session, state.classification_agent, state.knowledge, state.settings)


def get_drafting_service(request: Request, session: Annotated[Session, Depends(get_session)]) -> DraftingService:
    return DraftingService(session, request.app.state.drafting_agent)


def get_language_fusion_service(request: Request) -> Any:
    state = request.app.state
    if hasattr(state, "language_fusion") and state.language_fusion is not None:
        return state.language_fusion
    from app.services.language_detection.fusion_service import LanguageFusionService
    ai_provider = getattr(state, "ai_provider", None)
    if ai_provider is None and hasattr(state, "settings"):
        from app.services.ai.provider import build_ai_provider
        ai_provider = build_ai_provider(state.settings)
    languages = getattr(state, "languages", None)
    fusion = LanguageFusionService(ai_provider, languages)
    state.language_fusion = fusion
    return fusion


SettingsDep = Annotated[Settings, Depends(get_app_settings)]
DatabaseDep = Annotated[Database, Depends(get_database)]
ReferenceDep = Annotated[ReferenceRepository, Depends(get_reference)]
ComplaintServiceDep = Annotated[ComplaintService, Depends(get_complaint_service)]
AuditServiceDep = Annotated[AuditService, Depends(get_audit_service)]
IntakeServiceDep = Annotated[IntakeService, Depends(get_intake_service)]
ClassificationServiceDep = Annotated[ClassificationService, Depends(get_classification_service)]
DraftingServiceDep = Annotated[DraftingService, Depends(get_drafting_service)]
LanguageFusionDep = Annotated[Any, Depends(get_language_fusion_service)]

