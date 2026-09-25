from __future__ import annotations

from fastapi import APIRouter, Response, status

from app.api.deps import DatabaseDep, SettingsDep
from app.schemas.common import HealthResponse

router = APIRouter(tags=["health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    responses={503: {"model": HealthResponse, "description": "Database unreachable"}},
)
def health(settings: SettingsDep, db: DatabaseDep, response: Response) -> HealthResponse:
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
    )
