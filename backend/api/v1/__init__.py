from fastapi import APIRouter

from .health import router as health_router
from .meetings import router as meetings_router
from .auth import router as auth_router

router = APIRouter()
router.include_router(health_router)
router.include_router(meetings_router)
router.include_router(auth_router)
