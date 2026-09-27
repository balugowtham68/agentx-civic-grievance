from fastapi import APIRouter

from app.api.routes import classification, complaints, drafting, intake, watchdog, mock_gov, system

API_V1_PREFIX = "/api/v1"

api_router = APIRouter(prefix=API_V1_PREFIX)
api_router.include_router(complaints.router)
api_router.include_router(intake.router)
api_router.include_router(classification.router)
api_router.include_router(drafting.router)
api_router.include_router(watchdog.router)
api_router.include_router(mock_gov.router)
api_router.include_router(system.router)
