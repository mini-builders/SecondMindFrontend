"""
app/services/insights_service.py

Queries retained completed/archived tasks to generate user insights.
"""
from datetime import datetime, timedelta, timezone

from app.core.logger import get_logger
from app.db.client import get_tasks_collection, get_notification_events_collection

logger = get_logger(__name__)


async def get_user_insights(user_id: str) -> dict:
    """Generate insights from the user's historical task data."""
    tasks_col = get_tasks_collection()
    events_col = get_notification_events_collection()
    now = datetime.now(timezone.utc)

    # Overall counts
    total = await tasks_col.count_documents({"user_id": user_id})
    completed = await tasks_col.count_documents(
        {"user_id": user_id, "status": {"$in": ["completed", "archived"]}}
    )
    scheduled = await tasks_col.count_documents(
        {"user_id": user_id, "status": "scheduled"}
    )

    # Last 7 days
    week_ago = now - timedelta(days=7)
    completed_this_week = await tasks_col.count_documents({
        "user_id": user_id,
        "status": {"$in": ["completed", "archived"]},
        "updated_at": {"$gte": week_ago},
    })

    # Category breakdown of completed tasks
    pipeline = [
        {"$match": {
            "user_id": user_id,
            "status": {"$in": ["completed", "archived"]},
        }},
        {"$group": {"_id": "$category", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
    ]
    category_cursor = tasks_col.aggregate(pipeline)
    category_breakdown = {}
    async for doc in category_cursor:
        category_breakdown[doc["_id"]] = doc["count"]

    # Completion rate
    completion_rate = round((completed / total) * 100, 1) if total > 0 else 0.0

    # Total notifications fired
    total_fires = await events_col.count_documents({"user_id": user_id})

    return {
        "total_tasks": total,
        "completed_tasks": completed,
        "scheduled_tasks": scheduled,
        "completed_this_week": completed_this_week,
        "completion_rate_percent": completion_rate,
        "total_notifications_fired": total_fires,
        "category_breakdown": category_breakdown,
    }
