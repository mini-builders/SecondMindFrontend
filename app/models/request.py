from pydantic import BaseModel, Field


class ParseRequest(BaseModel):
    text: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Natural language task description",
        examples=["Remind me to call Rahul tomorrow at 7 PM"],
    )
