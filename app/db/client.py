from datetime import datetime, timedelta, timezone

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection

from app.core.config import settings

_client: AsyncIOMotorClient | None = None

CONFLICT_WINDOW_MINUTES = 15


async def connect() -> None:
    """Open the MongoDB connection."""
    global _client
    _client = AsyncIOMotorClient(settings.mongodb_uri)


async def disconnect() -> None:
    """Close the MongoDB connection."""
    global _client
    if _client:
        _client.close()
        _client = None


def get_tasks_collection() -> AsyncIOMotorCollection:
    return _client[settings.mongodb_database]["tasks"]


def get_notifications_collection() -> AsyncIOMotorCollection:
    return _client[settings.mongodb_database]["notifications"]


async def get_pending_notifications() -> list[dict]:
    """Return notifications due now that are not expired or acknowledged."""
    collection = get_notifications_collection()
    now = datetime.now(timezone.utc)
    cursor = collection.find(
        {
            "status": "pending",
            "scheduled_at": {"$lte": now},
            "$or": [
                {"expires": False},
                {"expires_at": {"$gt": now}},
            ],
        }
    )
    return await cursor.to_list(length=100)


async def acknowledge_notification(notification_id: str) -> bool:
    """Mark a notification as acknowledged. Returns True if updated."""
    from bson import ObjectId
    collection = get_notifications_collection()
    result = await collection.update_one(
        {"_id": ObjectId(notification_id), "status": "pending"},
        {"$set": {"status": "acknowledged"}},
    )
    return result.modified_count == 1


async def find_conflicting_task(
    collection: AsyncIOMotorCollection,
    scheduled_time: datetime,
) -> dict | None:
    """Return the first scheduled task within the conflict window, or None."""
    delta = timedelta(minutes=CONFLICT_WINDOW_MINUTES)
    return await collection.find_one(
        {
            "scheduled_time": {
                "$gte": scheduled_time - delta,
                "$lte": scheduled_time + delta,
            },
            "status": "scheduled",
        }
    )
