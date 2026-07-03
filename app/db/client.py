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


# ── Notification queries ──

def _pending_filter(user_id: str, now: datetime) -> dict:
    return {
        "user_id": user_id,
        "status": "pending",
        "$and": [
            {
                "$or": [
                    {"next_notify_at": {"$lte": now}},
                    {"next_notify_at": {"$exists": False}, "scheduled_at": {"$lte": now}},
                    {"next_notify_at": None, "scheduled_at": {"$lte": now}},
                ]
            },
            {
                "$or": [
                    {"expires": False},
                    {"expires_at": {"$gt": now}},
                ]
            },
        ],
    }


async def get_pending_notifications(user_id: str) -> list[dict]:
    """All pending notifications for the bell — shows everything until acknowledged."""
    cursor = get_notifications_collection().find(
        {"user_id": user_id, "status": "pending"},
        sort=[("scheduled_at", 1)],
    )
    return await cursor.to_list(length=100)


async def get_pending_notifications_count(user_id: str) -> int:
    return await get_notifications_collection().count_documents(
        {"user_id": user_id, "status": "pending"}
    )


async def advance_retry_notifications(user_id: str) -> None:
    """When bell is opened: snooze all retry notifications so they come back later."""
    collection = get_notifications_collection()
    now = datetime.now(timezone.utc)
    docs = await collection.find({
        **_pending_filter(user_id, now),
        "retry": True,
    }).to_list(length=100)

    for doc in docs:
        interval = doc.get("retry_interval_minutes", 10)
        await collection.update_one(
            {"_id": doc["_id"]},
            {"$set": {"next_notify_at": now + timedelta(minutes=interval)}},
        )


async def get_due_for_push(now: datetime) -> list[dict]:
    """Notifications due for a push: pending, next_notify_at <= now, not expired."""
    cursor = get_notifications_collection().find({
        "status": "pending",
        "$and": [
            {
                "$or": [
                    {"next_notify_at": {"$lte": now}},
                    {"next_notify_at": {"$exists": False}, "scheduled_at": {"$lte": now}},
                    {"next_notify_at": None, "scheduled_at": {"$lte": now}},
                ]
            },
            {
                "$or": [
                    {"expires": False},
                    {"expires_at": {"$gt": now}},
                ]
            },
        ],
    })
    return await cursor.to_list(length=500)


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


async def acknowledge_notification(notification_id: str, user_id: str) -> bool:
    collection = get_notifications_collection()
    result = await collection.update_one(
        {"_id": ObjectId(notification_id), "status": "pending", "user_id": user_id},
        {"$set": {"status": "acknowledged"}},
    )
    return result.modified_count == 1
