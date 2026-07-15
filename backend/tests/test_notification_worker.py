import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock, AsyncMock

from app.workers.notification_worker import _user_in_meeting, run_push_worker

@pytest.mark.asyncio
async def test_user_in_meeting_false():
    with patch("app.workers.notification_worker.get_tasks_collection") as mock_get_col:
        mock_col = MagicMock()
        mock_col.find_one = AsyncMock(return_value=None)
        mock_get_col.return_value = mock_col
        
        now = datetime.now(timezone.utc)
        result = await _user_in_meeting("user_123", now)
        assert result is False

@pytest.mark.asyncio
async def test_user_in_meeting_true():
    with patch("app.workers.notification_worker.get_tasks_collection") as mock_get_col:
        mock_col = MagicMock()
        now = datetime.now(timezone.utc)
        
        mock_col.find_one = AsyncMock(return_value={
            "scheduled_time": now - timedelta(minutes=10),
            "duration_minutes": 60
        })
        mock_get_col.return_value = mock_col
        
        result = await _user_in_meeting("user_123", now)
        assert result is True

@pytest.mark.asyncio
async def test_user_in_meeting_expired():
    with patch("app.workers.notification_worker.get_tasks_collection") as mock_get_col:
        mock_col = MagicMock()
        now = datetime.now(timezone.utc)
        
        mock_col.find_one = AsyncMock(return_value={
            "scheduled_time": now - timedelta(minutes=65),
            "duration_minutes": 60
        })
        mock_get_col.return_value = mock_col
        
        result = await _user_in_meeting("user_123", now)
        assert result is False

@pytest.mark.asyncio
async def test_run_push_worker_suppresses_in_meeting():
    with patch("app.workers.notification_worker.get_due_notification_configs", new_callable=AsyncMock) as mock_due, \
         patch("app.workers.notification_worker._user_in_meeting", new_callable=AsyncMock) as mock_in_meeting, \
         patch("app.workers.notification_worker.update_notification_after_fire", new_callable=AsyncMock) as mock_update, \
         patch("app.workers.notification_worker._expire_overdue", new_callable=AsyncMock):
        
        mock_due.return_value = [{
            "_id": "notif_1",
            "user_id": "user_123",
            "task_id": "task_1",
            "severity": "low",
            "task_type": "communication"
        }]
        
        mock_in_meeting.return_value = True
        
        await run_push_worker()
        
        mock_update.assert_called_once()
        args, kwargs = mock_update.call_args
        assert args[0] == "notif_1"
        assert "next_fire_at" in kwargs
