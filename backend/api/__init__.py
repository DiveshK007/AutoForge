"""
AutoForge API Router — Central route registry.
"""

from fastapi import APIRouter

from api.webhooks import router as webhooks_router
from api.agents import router as agents_router
from api.workflows import router as workflows_router
from api.telemetry import router as telemetry_router
from api.dashboard import router as dashboard_router
from api.auth import router as auth_router
from api.approvals import router as approvals_router

api_router = APIRouter()

api_router.include_router(webhooks_router, prefix="/webhooks", tags=["webhooks"])
api_router.include_router(agents_router, prefix="/agents", tags=["agents"])
api_router.include_router(workflows_router, prefix="/workflows", tags=["workflows"])
api_router.include_router(telemetry_router, prefix="/telemetry", tags=["telemetry"])
api_router.include_router(dashboard_router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(approvals_router, prefix="/approvals", tags=["approvals"])
