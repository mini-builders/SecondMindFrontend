from datetime import datetime, timedelta, timezone

from app.core.logger import get_logger
from app.db.client import (
    complete_notification_config,
    create_notification_event,
    expire_notification_config,
    expire_task_events,
    get_due_notification_configs,
    get_notifications_to_expire,
    get_push_subscriptions_for_user,
    update_notification_after_fire,
)
from app.services.push_service import send_push

logger = get_logger(__name__)


async def run_push_worker() -> None:
    now = datetime.now(timezone.utc)

    # Expire overdue configs first, then fire due ones
    await _expire_overdue(now)

    due = await get_due_notification_configs(now)
    if not due:
        return

    logger.info("Push worker | %d due", len(due))

    for config in due:
        fire_number = config.get("fire_count", 0) + 1

        await create_notification_event(config, fire_number, now)

        subs = await get_push_subscriptions_for_user(config["user_id"])
        for sub in subs:
            await send_push(
                sub,
                title=config["task_title"],
                body=_push_body(config, fire_number),
                data={"task_id": config["task_id"], "category": config.get("category", "Personal")},
            )

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


def _push_body(config: dict, fire_number: int) -> str:
    title = config.get("task_title", "Reminder")
    if fire_number == 1:
        return f"{title}"
    return f"Reminder #{fire_number}: {title}"
