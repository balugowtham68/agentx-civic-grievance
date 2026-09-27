"""Mock Government endpoints for demo simulation."""

from typing import Annotated
from pydantic import BaseModel

from fastapi import APIRouter, Depends, Request, HTTPException
from app.schemas.enums import AuthorityStatus

router = APIRouter(prefix="/mock-government", tags=["mock_government"])

class StatusUpdateRequest(BaseModel):
    status: AuthorityStatus

@router.post("/complaints/{tracking_id}/status")
async def update_mock_status(tracking_id: str, payload: StatusUpdateRequest, request: Request):
    """Simulate an authority updating the grievance status."""
    mock_gov = request.app.state.mock_gov
    if tracking_id not in mock_gov._grievances:
        raise HTTPException(status_code=404, detail="Mock complaint not found")
        
    mock_gov._grievances[tracking_id].status = payload.status
    return {"tracking_id": tracking_id, "status": payload.status}

@router.post("/complaints/{tracking_id}/resolve")
async def resolve_mock_complaint(tracking_id: str, request: Request):
    """Simulate an authority resolving the grievance."""
    mock_gov = request.app.state.mock_gov
    if tracking_id not in mock_gov._grievances:
        raise HTTPException(status_code=404, detail="Mock complaint not found")
        
    mock_gov._grievances[tracking_id].status = AuthorityStatus.RESOLVED
    return {"tracking_id": tracking_id, "status": AuthorityStatus.RESOLVED}

@router.get("/complaints/{tracking_id}")
async def get_mock_complaint(tracking_id: str, request: Request):
    """Get the raw mock government record."""
    mock_gov = request.app.state.mock_gov
    if tracking_id not in mock_gov._grievances:
        raise HTTPException(status_code=404, detail="Mock complaint not found")
    
    record = mock_gov._grievances[tracking_id]
    return {
        "tracking_id": record.tracking_id,
        "status": record.status,
    }
