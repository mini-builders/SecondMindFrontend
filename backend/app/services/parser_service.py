from datetime import datetime, timezone, timedelta

from app.core.notification_rules import get_rules

_IST = timezone(timedelta(hours=5, minutes=30))
from app.db.client import find_conflicting_task, get_notifications_collection, get_tasks_collection
from app.exceptions import TaskConflictError
from app.models.notification import NotificationDocument
from app.models.response import ParseResponse
from app.core.logger import get_logger

logger = get_logger(__name__)


def _to_datetime(value: str | None) -> datetime | None:
    if value is None:
        return None
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=_IST)
    return dt


async def parse_task(
    text: str,
    raw: dict,
    user_id: str,
    category: str | None = None,
    priority: str | None = None,
) -> ParseResponse:
    scheduled_time = _to_datetime(raw.get("scheduled_time"))
    final_category = category if category else raw.get("category", "personal")
    
    # Read the new severity field instead of priority
    final_severity = priority if priority else raw.get("severity", "medium")
    duration = raw.get("duration_minutes", 15)
    is_blocking = raw.get("is_blocking", False)
    time_window = raw.get("time_window", None)
    
    rules = get_rules(final_category, final_severity)
    tasks_collection = get_tasks_collection()

    if scheduled_time:
        existing = await find_conflicting_task(tasks_collection, scheduled_time, duration, user_id)
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
    anchor = scheduled_time or now
    expires_at = (anchor + rules["expires_delta"]) if rules["expires"] and rules["expires_delta"] else None

    task_doc = {
        "user_id": user_id,
        "title": raw["title"],
        "original_text": text,
        "task_type": raw["task_type"],
        "category": final_category,
        "severity": final_severity,
        "severity_source": "ai_inferred",
        "duration_minutes": duration,
        "is_blocking": is_blocking,
        "time_window": time_window,
        "scheduled_time": scheduled_time,
        "status": "scheduled",
        "retry_count": 0,
        "created_at": now,
        "updated_at": now,
    }

    task_result = await tasks_collection.insert_one(task_doc)
    task_doc["_id"] = task_result.inserted_id

    logger.info(
        "Task saved | id=%s | title=%s | category=%s | user_id=%s",
        task_result.inserted_id, raw["title"], final_category, user_id,
    )

    notification_doc = {
        "user_id": user_id,
        "task_id": str(task_result.inserted_id),
        "task_title": raw["title"],
        "task_type": raw["task_type"],
        "category": final_category,
        "severity": final_severity,
        "scheduled_at": scheduled_time,
        "next_fire_at": scheduled_time or now,
        "snooze_until": None,
        "max_fires": rules["max_fires"],
        "fire_count": 0,
        "status": "active",
        "retry": rules["retry"],
        "retry_interval_minutes": rules["retry_interval_minutes"],
        "expires": rules["expires"],
        "expires_at": expires_at,
        "created_at": now,
    }

    notifications_collection = get_notifications_collection()
    notification_result = await notifications_collection.insert_one(notification_doc)
    notification_doc["_id"] = notification_result.inserted_id

    logger.info(
        "Notification saved | id=%s | category=%s | retry=%s | interval=%smin | expires=%s",
        notification_result.inserted_id, final_category, rules["retry"],
        rules["retry_interval_minutes"], expires_at,
    )

    return ParseResponse(
        **task_doc,
        notification=NotificationDocument(**notification_doc),
    )
