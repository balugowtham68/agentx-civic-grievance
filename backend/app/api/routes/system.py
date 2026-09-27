"""System endpoints for demo and monitoring."""

from fastapi import APIRouter, Request, HTTPException
from sqlalchemy import text
from app.api.deps import DatabaseDep, SettingsDep

router = APIRouter(tags=["system"])

@router.get("/system/status")
async def system_status(settings: SettingsDep, db: DatabaseDep, request: Request):
    """Return useful information about system components."""
    db_ok = db.is_reachable()
    
    mock_gov = getattr(request.app.state, "mock_gov", None)
    watchdog = getattr(request.app.state, "watchdog_agent", None)
    
    return {
        "backend": "ok",
        "database": "ok" if db_ok else "unavailable",
        "watchdog": "running" if watchdog else "stopped",
        "mock_government": "ok" if mock_gov else "unavailable",
        "ai_provider": "available" if settings.gemini_api_key else "fallback"
    }

@router.post("/demo/reset")
async def demo_reset(settings: SettingsDep, db: DatabaseDep, request: Request):
    """Safely clear demo complaints when in demo mode."""
    if not settings.demo_mode:
        raise HTTPException(status_code=403, detail="Reset only allowed in demo mode")
        
    try:
        with db.session() as session:
            # We truncate all complaint-related tables.
            session.execute(text("TRUNCATE TABLE escalations, sla_records, audit_events, complaint_drafts, classification_records, intake_records, complaints CASCADE;"))
            session.commit()
            
        # Also reset mock government memory
        mock_gov = getattr(request.app.state, "mock_gov", None)
        if mock_gov:
            mock_gov._grievances.clear()
            
        return {"status": "success", "message": "Demo data reset successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
