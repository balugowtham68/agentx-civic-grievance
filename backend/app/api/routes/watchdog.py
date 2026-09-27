"""Watchdog endpoints for demo and triggering."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.services.watchdog_service import WatchdogService
from app.api.deps import get_session
from sqlalchemy.orm import Session

router = APIRouter(prefix="/watchdog", tags=["watchdog"])

@router.post("/run")
async def run_watchdog(request: Request, session: Annotated[Session, Depends(get_session)]) -> dict[str, int]:
    """Execute one watchdog cycle immediately."""
    watchdog_agent = request.app.state.watchdog_agent
    service = WatchdogService(session, watchdog_agent)
    stats = await service.run_cycle()
    return stats
