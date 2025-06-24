from fastapi import APIRouter, Header, BackgroundTasks, Request, Response

from workers.task import process_drive_notification
from services.drive_client import parse_drive_headers
from core.logging import logger

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


@router.post("/drive", include_in_schema=False)
async def drive_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_goog_channel_id: str = Header(default=""),
):
    """
    Google posts an **empty** body, info is entirely in headers.
    We acknowledge immediately and let Celery do the heavy work.
    """
    header_map = parse_drive_headers(request.headers)
    logger.info(
        "[DriveWebhook] recv channel={} resourceId={} userToken={}",
        header_map.get("x-goog-channel-id"),
        header_map.get("x-goog-resource-id")[:8],
        header_map.get("x-goog-channel-token"),
    )
    background_tasks.add_task(process_drive_notification.delay, header_map)
    # Drive requires 2xx response within 10 seconds
    return Response(status_code=204)
