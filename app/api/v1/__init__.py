from fastapi import APIRouter
from app.api.v1.endpoints import identify, enroll_old as enroll, enroll_s3, system

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(identify.router, tags=["Identification"])
api_router.include_router(enroll.router, tags=["Enrollment"])
api_router.include_router(enroll_s3.router, tags=["Enrollment"])
api_router.include_router(system.router, tags=["System"])

__all__ = ["api_router", "identify", "enroll", "enroll_s3", "system"]
