from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field
from pydantic.functional_validators import BeforeValidator

from app.core.timezone import ISTDatetime

PyObjectId = Annotated[str, BeforeValidator(str)]


class TaskDocument(BaseModel):
    id: PyObjectId = Field(alias="_id")
    user_id: str
    title: str
    original_text: str
    task_type: str
    category: str = "Personal"
    severity: str = "medium"
    severity_source: str = "ai_inferred"
    duration_minutes: int | None = None
    is_blocking: bool = False
    time_window: dict | None = None
    scheduled_time: ISTDatetime | None
    status: str
    retry_count: int
    created_at: ISTDatetime
    updated_at: ISTDatetime

    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
