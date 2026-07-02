from datetime import datetime, timezone

from app.db.client import find_conflicting_task, get_notifications_collection, get_tasks_collection
from app.exceptions import TaskConflictError
from app.llm.client import get_groq_client
from app.llm.parser import extract_task_from_text
from app.models.notification import NotificationDocument
from app.models.response import ParseResponse
from app.core.logger import get_logger

logger = get_logger(__name__)


def _to_datetime(value: str | None) -> datetime | None:
    if value is None:
        return None
    return datetime.fromisoformat(value)


async def parse_task(text: str) -> ParseResponse:
    """Extract task from natural language, check for conflicts, persist task + notification."""
    client = get_groq_client()
    raw = await extract_task_from_text(client, text)

    scheduled_time = _to_datetime(raw.get("scheduled_time"))
    tasks_collection = get_tasks_collection()

    if scheduled_time:
        existing = await find_conflicting_task(tasks_collection, scheduled_time)
        if existing:
            logger.warning(
                "Time conflict | new=%s | existing=%s (%s)",
                raw["title"], existing["title"], existing["_id"],
            )
            raise TaskConflictError(
                conflicting_task_id=str(existing["_id"]),
                conflicting_task_title=existing["title"],
            )

    now = datetime.now(timezone.utc)

    task_doc = {
        "title": raw["title"],
        "original_text": text,
        "task_type": raw["task_type"],
        "scheduled_time": scheduled_time,
        "status": "scheduled",
        "retry_count": 0,
        "created_at": now,
        "updated_at": now,
    }

    task_result = await tasks_collection.insert_one(task_doc)
    task_doc["_id"] = task_result.inserted_id

    logger.info(
        "Task saved | id=%s | title=%s | task_type=%s",
        task_result.inserted_id, raw["title"], raw["task_type"],
    )

    notification_doc = {
        "task_id": str(task_result.inserted_id),
        "task_title": raw["title"],
        "task_type": raw["task_type"],
        "scheduled_at": scheduled_time,
        "status": "pending",
        "retry": raw.get("retry", False),
        "retry_interval_minutes": raw.get("retry_interval_minutes", 0),
        "expires": raw.get("expires", False),
        "expires_at": _to_datetime(raw.get("expires_at")),
        "created_at": now,
    }

    notifications_collection = get_notifications_collection()
    notification_result = await notifications_collection.insert_one(notification_doc)
    notification_doc["_id"] = notification_result.inserted_id

    logger.info(
        "Notification saved | id=%s | task_id=%s | retry=%s | expires=%s",
        notification_result.inserted_id, task_result.inserted_id,
        raw.get("retry"), raw.get("expires"),
    )

    return ParseResponse(
        **task_doc,
        notification=NotificationDocument(**notification_doc),
    )
