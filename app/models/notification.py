from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field
from pydantic.functional_validators import BeforeValidator

from app.core.timezone import ISTDatetime

PyObjectId = Annotated[str, BeforeValidator(str)]


class NotificationDocument(BaseModel):
    """Notification config — one per task, read by the scheduler."""
    id: PyObjectId = Field(alias="_id")
    user_id: str
    task_id: str
    task_title: str
    task_type: str
    category: str = "Personal"
    scheduled_at: ISTDatetime | None = None
    next_fire_at: ISTDatetime
    fire_count: int = 0
    status: str = "active"  # active | completed | expired
    retry: bool
    retry_interval_minutes: int
    expires: bool
    expires_at: ISTDatetime | None = None
    created_at: ISTDatetime

    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)


class NotificationEventDocument(BaseModel):
    """A single fired notification instance — what the bell shows."""
    id: PyObjectId = Field(alias="_id")
    user_id: str
    notification_id: str
    task_id: str
    task_title: str
    task_type: str
    category: str = "Personal"
    fired_at: ISTDatetime
    fire_number: int
    status: str  # pending | task_expired
    created_at: ISTDatetime

    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
