from datetime import datetime, timedelta, timezone

from app.core.logger import get_logger
from app.db.client import (
    get_due_for_push,
    get_notifications_collection,
    get_push_subscriptions_for_user,
)
from app.services.push_service import send_push

logger = get_logger(__name__)


async def run_push_worker() -> None:
    """Called every 60 s by APScheduler — sends web push for due notifications."""
    now = datetime.now(timezone.utc)
    docs = await get_due_for_push(now)

    if not docs:
        return

    logger.info("Push worker | %d due notifications", len(docs))

    for doc in docs:
        user_id = doc.get("user_id", "")
        subs = await get_push_subscriptions_for_user(user_id)
        if not subs:
            continue

        title = doc.get("task_title", "Reminder")
        task_type = doc.get("task_type", "personal")
        body = _body_for_type(task_type, title)

        sent_any = False
        for sub in subs:
            ok = await send_push(
                sub,
                title=title,
                body=body,
                data={"notification_id": str(doc["_id"]), "task_type": task_type},
            )
            if ok:
                sent_any = True

        if sent_any and doc.get("retry"):
            interval = doc.get("retry_interval_minutes", 10) or 10
            next_at = now + timedelta(minutes=interval)
            await get_notifications_collection().update_one(
                {"_id": doc["_id"]},
                {"$set": {"next_notify_at": next_at}},
            )
            logger.debug("Scheduled retry | id=%s | next=%s", doc["_id"], next_at)


def _body_for_type(task_type: str, title: str) -> str:
    prompts = {
        "medicine": "Time to take your medicine.",
        "meeting": "Your meeting is coming up.",
        "communication": "Don't forget to follow up.",
        "live_event": "It's starting soon!",
        "errand": "Don't forget this errand.",
    }
    return prompts.get(task_type, f"Reminder: {title}")
