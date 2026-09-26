"""SPANDAN AI backend entry point.

Run locally:  uvicorn app.main:app --port 8000   (from backend/)
"""

from __future__ import annotations

import time
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.api.routes import health
from app.core.config import Settings, get_settings
from app.core.errors import ErrorBody, ErrorResponse, register_error_handlers
from app.core.languages import LanguageRegistry
from app.core.logging import configure_logging, get_logger, request_id_var
from app.database import Database
from app.repositories import ReferenceRepository
from app.services.classification.factory import build_classification_agent, build_knowledge_base
from app.services.drafting.factory import build_drafting_agent
from app.services.intake.factory import build_intake_agent
from app.services.knowledge import KnowledgeBaseError

logger = get_logger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        db = Database(settings.database_url)
        db.init_schema()
        reference = ReferenceRepository(settings.knowledge_base_dir)
        _ = reference.data  # validate knowledge-base config now; fail fast if broken
        languages = LanguageRegistry.load()
        app.state.settings = settings
        app.state.db = db
        app.state.reference = reference
        app.state.languages = languages
        app.state.intake_agent = build_intake_agent(settings, languages)
        # Phase 3: malformed knowledge records stop start-up (build_knowledge_base raises).
        knowledge = build_knowledge_base(settings, reference)
        app.state.knowledge = knowledge
        app.state.classification_agent = build_classification_agent(settings, reference, knowledge)
        app.state.drafting_agent = build_drafting_agent(settings, reference, languages)
        try:
            status = knowledge.ensure_ready(auto_ingest=settings.kb_auto_ingest)
            logger.info("civic knowledge base ready", extra={"records": status.records, "embedder": status.embedder})
        except KnowledgeBaseError as exc:
            # Intake keeps working; classification answers 503 until the KB is ingested.
            logger.error("civic knowledge base not ready", extra={"error": str(exc)})
        logger.info("SPANDAN AI backend started", extra={"config": settings.summary()})
        try:
            yield
        finally:
            db.dispose()
            logger.info("SPANDAN AI backend stopped")

    app = FastAPI(
        title=f"{settings.app_name} API",
        version=settings.app_version,
        description=(
            "SPANDAN AI - Listen. Respond. Resolve. Autonomous Civic Grievance Redressal Agent. "
            "Citizen intake and classification work offline; external AI is optional. Hackathon prototype: "
            "government integration is a mock and SLA time can be simulated."
        ),
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "X-Request-ID"],
        expose_headers=["X-Request-ID"],
    )

    @app.middleware("http")
    async def limit_request_size(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        # Rejects oversized bodies before they are read (the voice route also
        # enforces the limit while streaming, for requests without Content-Length).
        declared = request.headers.get("content-length", "")
        if declared.isdigit() and int(declared) > settings.max_audio_bytes:
            body = ErrorResponse(
                error=ErrorBody(code="payload_too_large", message="Request body is too large")
            )
            return JSONResponse(status_code=413, content=body.model_dump())
        return await call_next(request)

    @app.middleware("http")
    async def request_context(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        incoming = request.headers.get("X-Request-ID", "")
        request_id = incoming if 0 < len(incoming) <= 64 else uuid.uuid4().hex
        token = request_id_var.set(request_id)
        started = time.perf_counter()
        try:
            response = await call_next(request)
        finally:
            request_id_var.reset(token)
        response.headers["X-Request-ID"] = request_id
        logger.info(
            "request",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "duration_ms": round((time.perf_counter() - started) * 1000, 1),
            },
        )
        return response

    register_error_handlers(app)
    app.include_router(health.router)
    app.include_router(api_router)
    return app


app = create_app()
