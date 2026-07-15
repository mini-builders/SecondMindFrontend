from datetime import datetime, timedelta, timezone

import httpx

from app.core.logger import get_logger
from app.db.client import (
    complete_notification_config,
    create_notification_event,
    expire_notification_config,
    expire_task_events,
    get_due_notification_configs,
    get_notifications_to_expire,
    get_tasks_collection,
    get_user_by_id,
    update_notification_after_fire,
)

logger = get_logger(__name__)


async def _user_in_meeting(user_id: str, now: datetime) -> bool:
    """Check if the user currently has an active meeting task."""
    tasks_col = get_tasks_collection()
    meeting = await tasks_col.find_one({
        "user_id": user_id,
        "task_type": "meeting",
        "status": "scheduled",
        "scheduled_time": {"$lte": now},
    })
    if not meeting:
        return False
    # Check if the meeting is still ongoing based on its duration
    duration = meeting.get("duration_minutes", 60)
    end_time = meeting["scheduled_time"] + timedelta(minutes=duration)
    return now < end_time


async def run_push_worker() -> None:
    now = datetime.now(timezone.utc)

    # Expire overdue configs first, then fire due ones
    await _expire_overdue(now)

    due = await get_due_notification_configs(now)
    if not due:
        return

    logger.info("Push worker | %d due", len(due))

    for config in due:
        # Meeting suppression: defer low/medium if user is in a meeting
        task_severity = config.get("severity", "medium")
        if task_severity != "high" and config.get("task_type") != "meeting":
            if await _user_in_meeting(config["user_id"], now):
                logger.info(
                    "Suppressed (meeting active) | task=%s | severity=%s",
                    config["task_id"], task_severity,
                )
                # Defer by 5 minutes and recheck
                await update_notification_after_fire(
                    config["_id"],
                    next_fire_at=now + timedelta(minutes=5),
                    fire_count=config.get("fire_count", 0),
                )
                continue

        fire_number = config.get("fire_count", 0) + 1

        await create_notification_event(config, fire_number, now)
        await _send_whatsapp(config)

        if config.get("retry"):
            interval = config.get("retry_interval_minutes", 20) or 20
            await update_notification_after_fire(
                config["_id"],
                next_fire_at=now + timedelta(minutes=interval),
                fire_count=fire_number,
            )
        else:
            await complete_notification_config(config["_id"])

        logger.debug("Fired | task=%s | fire#=%d | retry=%s", config["task_id"], fire_number, config.get("retry"))


async def _expire_overdue(now: datetime) -> None:
    configs = await get_notifications_to_expire(now)
    for config in configs:
        await expire_notification_config(config["_id"])
        await expire_task_events(config["task_id"], config["user_id"])
        logger.info("Expired | task=%s | total_fires=%d", config["task_id"], config.get("fire_count", 0))


async def _send_whatsapp(config: dict) -> None:
    from app.services.whatsapp_service import send_reminder, send_text

    user = await get_user_by_id(config["user_id"])
    if not user or not user.get("mobile"):
        return

    wa_id = user["mobile"].lstrip("+")
    task_id = config["task_id"]
    task_title = config["task_title"]

    try:
        result = await send_reminder(wa_id, task_title, task_id)
        logger.info("WhatsApp sent | wa_id=%s | task=%s | result=%s", wa_id, task_id, result)
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 400:
            # Outside 24h session window — fall back to plain text
            try:
                result = await send_text(wa_id, f"🔔 Reminder: {task_title}\n\nReply to this message to use Done/Snooze buttons.")
                logger.info("WhatsApp fallback text sent | wa_id=%s | task=%s", wa_id, task_id)
            except Exception as fallback_exc:
                logger.warning("WhatsApp fallback failed | wa_id=%s | task=%s | error=%s", wa_id, task_id, fallback_exc)
        else:
            logger.warning(
                "WhatsApp failed | wa_id=%s | task=%s | status=%s | body=%s",
                wa_id, task_id, exc.response.status_code, exc.response.text,
            )
    except Exception as exc:
        logger.warning("WhatsApp error | wa_id=%s | task=%s | error=%s", wa_id, task_id, exc)
