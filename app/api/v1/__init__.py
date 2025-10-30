from fastapi import APIRouter
from app.api.v1.endpoints import identify, enroll, system

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(identify.router, tags=["Identification"])
api_router.include_router(enroll.router, tags=["Enrollment"])
api_router.include_router(system.router, tags=["System"])

__all__ = ["api_router", "identify", "enroll", "system"]
