from fastapi import APIRouter, Depends, HTTPException, status

from app.core.auth import get_current_user
from app.core.logger import get_logger
from app.db.client import (
    acknowledge_notification,
    advance_retry_notifications,
    get_pending_notifications,
    get_pending_notifications_count,
)
from app.models.notification import NotificationDocument

logger = get_logger(__name__)

router = APIRouter()


@router.get("/count")
async def pending_count(current_user: dict = Depends(get_current_user)) -> dict:
    """Badge count — called silently every 30s by the frontend."""
    count = await get_pending_notifications_count(str(current_user["_id"]))
    return {"count": count}


@router.post("/seen-all", status_code=status.HTTP_200_OK)
async def seen_all(current_user: dict = Depends(get_current_user)) -> dict:
    """Called when bell is opened — advances retry notifications so they come back later."""
    await advance_retry_notifications(str(current_user["_id"]))
    return {"ok": True}


@router.get("", response_model=list[NotificationDocument])
async def list_pending_notifications(
    current_user: dict = Depends(get_current_user),
) -> list[NotificationDocument]:
    docs = await get_pending_notifications(str(current_user["_id"]))
    return [NotificationDocument(**doc) for doc in docs]


@router.patch("/{notification_id}/acknowledge", status_code=status.HTTP_200_OK)
async def acknowledge(
    notification_id: str,
    current_user: dict = Depends(get_current_user),
) -> dict:
    updated = await acknowledge_notification(notification_id, str(current_user["_id"]))
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found or already acknowledged.",
        )
    logger.info("Notification acknowledged | id=%s", notification_id)
    return {"acknowledged": True}
