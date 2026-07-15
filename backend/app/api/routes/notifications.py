from fastapi import APIRouter, Depends, status

from app.core.auth import get_current_user
from app.core.logger import get_logger
from app.db.client import get_bell_events, get_bell_events_count, mark_task_done
from app.models.notification import NotificationEventDocument

logger = get_logger(__name__)

router = APIRouter()


@router.get("/count")
async def bell_count(current_user: dict = Depends(get_current_user)) -> dict:
    count = await get_bell_events_count(str(current_user["_id"]))
    return {"count": count}


@router.get("", response_model=list[NotificationEventDocument])
async def list_bell_events(
    current_user: dict = Depends(get_current_user),
) -> list[NotificationEventDocument]:
    docs = await get_bell_events(str(current_user["_id"]))
    return [NotificationEventDocument(**doc) for doc in docs]


@router.post("/{task_id}/done", status_code=status.HTTP_200_OK)
async def done_task(
    task_id: str,
    current_user: dict = Depends(get_current_user),
) -> dict:
    await mark_task_done(task_id, str(current_user["_id"]))
    logger.info("Task done | task_id=%s | user_id=%s", task_id, current_user["_id"])
    return {"ok": True}
