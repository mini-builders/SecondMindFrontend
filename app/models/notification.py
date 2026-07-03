from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field
from pydantic.functional_validators import BeforeValidator

PyObjectId = Annotated[str, BeforeValidator(str)]


class NotificationDocument(BaseModel):
    id: PyObjectId = Field(alias="_id")
    user_id: str
    task_id: str
    task_title: str
    task_type: str
    category: str = "Personal"
    scheduled_at: datetime | None = None
    next_notify_at: datetime | None = None
    status: str   # pending | acknowledged | expired
    retry: bool
    retry_interval_minutes: int
    expires: bool
    expires_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(populate_by_name=True)
