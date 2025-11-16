"""
NexusAI Platform - API v1 Router
Combines all route modules
"""

from fastapi import APIRouter

from backend.api.v1.routes import (
    auth,
    models,
    inference,
    cameras,
    users,
    settings,
    yolo,
)

# Create main v1 router
api_v1_router = APIRouter(prefix="/api/v1")

# Include all route modules
api_v1_router.include_router(auth.router)
api_v1_router.include_router(models.router)
api_v1_router.include_router(inference.router)
api_v1_router.include_router(cameras.router)
api_v1_router.include_router(users.router)
api_v1_router.include_router(settings.router)
api_v1_router.include_router(yolo.router)
