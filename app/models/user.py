from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field
from pydantic.functional_validators import BeforeValidator

PyObjectId = Annotated[str, BeforeValidator(str)]


class UserDocument(BaseModel):
    id: PyObjectId = Field(alias="_id")
    name: str
    mobile: str
    email: str | None = None
    password_hash: str
    created_at: datetime

    model_config = ConfigDict(populate_by_name=True)
