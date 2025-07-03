from fastapi import APIRouter

from .health import router as health_router
from .meetings import router as meetings_router
from .auth import router as auth_router
from .calendar import router as calendar_router
from .notifications import router as notifications_router
from .tasks import router as tasks_router
# from .webhooks import router as webhooks_router  # Commented out for local development

router = APIRouter()
router.include_router(health_router)
router.include_router(meetings_router)
router.include_router(auth_router)
router.include_router(calendar_router)
router.include_router(notifications_router)
router.include_router(tasks_router)
# router.include_router(webhooks_router)  # Commented out for local development
