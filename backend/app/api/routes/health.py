from __future__ import annotations

from fastapi import APIRouter, Request, Response, status

from app.api.deps import DatabaseDep, SettingsDep
from app.schemas.common import HealthResponse

router = APIRouter(tags=["health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    responses={503: {"model": HealthResponse, "description": "Database unreachable"}},
)
def health(settings: SettingsDep, db: DatabaseDep, response: Response, request: Request) -> HealthResponse:
    """Liveness plus a lightweight database and configuration check."""
    db_ok = db.is_reachable()
    if not db_ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return HealthResponse(
        status="ok" if db_ok else "degraded",
        service=settings.app_name,
        version=settings.app_version,
        environment=settings.app_env.value,
        database="ok" if db_ok else "unavailable",
        configuration=settings.summary(),
        knowledge_base=_knowledge_base(request),
    )


def _knowledge_base(request: Request) -> dict[str, object] | None:
    knowledge = getattr(request.app.state, "knowledge", None)
    if knowledge is None:
        return None
    try:
        kb = knowledge.status()
    except Exception:  # noqa: BLE001 - health must never raise
        return {"ready": False}
    return {"ready": kb.ready, "records": kb.records, "embedder": kb.embedder, "stale": kb.stale}
