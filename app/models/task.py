from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field
from pydantic.functional_validators import BeforeValidator

PyObjectId = Annotated[str, BeforeValidator(str)]


class TaskDocument(BaseModel):
    id: PyObjectId = Field(alias="_id")
    user_id: str
    title: str
    original_text: str
    task_type: str
    category: str = "Personal"
    priority: str = "medium"
    scheduled_time: datetime | None
    status: str
    retry_count: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
