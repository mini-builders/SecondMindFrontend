from datetime import datetime, timedelta, timezone

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection

from app.core.config import settings

_client: AsyncIOMotorClient | None = None

CONFLICT_WINDOW_MINUTES = 15


async def connect() -> None:
    global _client
    _client = AsyncIOMotorClient(settings.mongodb_uri)


async def disconnect() -> None:
    global _client
    if _client:
        _client.close()
        _client = None


# ── Collections ──

def get_tasks_collection() -> AsyncIOMotorCollection:
    return _client[settings.mongodb_database]["tasks"]


def get_notifications_collection() -> AsyncIOMotorCollection:
    return _client[settings.mongodb_database]["notifications"]


def get_notification_events_collection() -> AsyncIOMotorCollection:
    return _client[settings.mongodb_database]["notification_events"]


def get_users_collection() -> AsyncIOMotorCollection:
    return _client[settings.mongodb_database]["users"]


def get_push_subscriptions_collection() -> AsyncIOMotorCollection:
    return _client[settings.mongodb_database]["push_subscriptions"]


# ── User queries ──

async def get_user_by_mobile(mobile: str) -> dict | None:
    return await get_users_collection().find_one({"mobile": mobile})


async def get_user_by_id(user_id: str) -> dict | None:
    return await get_users_collection().find_one({"_id": ObjectId(user_id)})


async def create_user(name: str, mobile: str, password_hash: str) -> dict:
    now = datetime.now(timezone.utc)
    doc = {"name": name, "mobile": mobile, "password_hash": password_hash, "created_at": now}
    result = await get_users_collection().insert_one(doc)
    doc["_id"] = result.inserted_id
    return doc


# ── Task queries ──

async def find_conflicting_task(
    collection: AsyncIOMotorCollection,
    scheduled_time: datetime,
    user_id: str,
) -> dict | None:
    delta = timedelta(minutes=CONFLICT_WINDOW_MINUTES)
    return await collection.find_one(
        {
            "user_id": user_id,
            "scheduled_time": {
                "$gte": scheduled_time - delta,
                "$lte": scheduled_time + delta,
            },
            "status": "scheduled",
        }
    )


# ── Notification config (scheduler reads) ──

async def get_due_notification_configs(now: datetime) -> list[dict]:
    """Active configs whose next_fire_at has arrived."""
    cursor = get_notifications_collection().find({
        "status": "active",
        "next_fire_at": {"$lte": now},
    })
    return await cursor.to_list(length=500)


async def get_notifications_to_expire(now: datetime) -> list[dict]:
    """Active configs whose expiry window has passed."""
    cursor = get_notifications_collection().find({
        "status": "active",
        "expires": True,
        "expires_at": {"$lte": now},
    })
    return await cursor.to_list(length=500)


async def update_notification_after_fire(notification_id, next_fire_at: datetime, fire_count: int) -> None:
    await get_notifications_collection().update_one(
        {"_id": notification_id},
        {"$set": {"next_fire_at": next_fire_at, "fire_count": fire_count}},
    )


async def complete_notification_config(notification_id) -> None:
    await get_notifications_collection().update_one(
        {"_id": notification_id},
        {"$set": {"status": "completed"}},
    )


async def expire_notification_config(notification_id) -> None:
    await get_notifications_collection().update_one(
        {"_id": notification_id},
        {"$set": {"status": "expired"}},
    )


# ── Notification events (bell reads) ──

async def create_notification_event(config: dict, fire_number: int, fired_at: datetime) -> dict:
    doc = {
        "user_id": config["user_id"],
        "notification_id": str(config["_id"]),
        "task_id": config["task_id"],
        "task_title": config["task_title"],
        "task_type": config.get("task_type", "personal"),
        "category": config.get("category", "Personal"),
        "fired_at": fired_at,
        "fire_number": fire_number,
        "status": "pending",
        "created_at": fired_at,
    }
    result = await get_notification_events_collection().insert_one(doc)
    doc["_id"] = result.inserted_id
    return doc


async def expire_task_events(task_id: str, user_id: str) -> None:
    """Mark all pending events for a task as task_expired."""
    await get_notification_events_collection().update_many(
        {"task_id": task_id, "user_id": user_id, "status": "pending"},
        {"$set": {"status": "task_expired"}},
    )


async def get_bell_events(user_id: str) -> list[dict]:
    """All events shown in the bell — pending fires and expired task events."""
    cursor = get_notification_events_collection().find(
        {"user_id": user_id, "status": {"$in": ["pending", "task_expired"]}},
        sort=[("fired_at", -1)],
    )
    return await cursor.to_list(length=200)


async def get_bell_events_count(user_id: str) -> int:
    return await get_notification_events_collection().count_documents(
        {"user_id": user_id, "status": {"$in": ["pending", "task_expired"]}}
    )


async def mark_task_done(task_id: str, user_id: str) -> None:
    """User marked task done — delete all its events and stop the config."""
    await get_notification_events_collection().delete_many(
        {"task_id": task_id, "user_id": user_id},
    )
    await get_notifications_collection().update_many(
        {"task_id": task_id, "user_id": user_id},
        {"$set": {"status": "completed"}},
    )


# ── Push subscriptions ──

async def get_push_subscriptions_for_user(user_id: str) -> list[dict]:
    cursor = get_push_subscriptions_collection().find({"user_id": user_id})
    return await cursor.to_list(length=20)


async def save_push_subscription(user_id: str, subscription: dict) -> None:
    endpoint = subscription.get("endpoint", "")
    await get_push_subscriptions_collection().update_one(
        {"user_id": user_id, "endpoint": endpoint},
        {"$set": {**subscription, "user_id": user_id}},
        upsert=True,
    )


async def delete_push_subscription(endpoint: str) -> None:
    await get_push_subscriptions_collection().delete_one({"endpoint": endpoint})
