from fastapi import APIRouter, HTTPException, status

from app.core.logger import get_logger
from app.db.client import acknowledge_notification, get_pending_notifications
from app.models.notification import NotificationDocument

logger = get_logger(__name__)

router = APIRouter()


@router.get("", response_model=list[NotificationDocument])
async def list_pending_notifications() -> list[NotificationDocument]:
    """Return all notifications that are due and not yet acknowledged."""
    docs = await get_pending_notifications()
    return [NotificationDocument(**doc) for doc in docs]


@router.patch("/{notification_id}/acknowledge", status_code=status.HTTP_200_OK)
async def acknowledge(notification_id: str) -> dict:
    """Mark a notification as acknowledged (user dismissed it)."""
    updated = await acknowledge_notification(notification_id)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found or already acknowledged.",
        )
    logger.info("Notification acknowledged | id=%s", notification_id)
    return {"acknowledged": True}
