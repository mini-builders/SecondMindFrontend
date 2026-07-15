from datetime import datetime, timedelta, timezone
from typing import Annotated

from pydantic import PlainSerializer

IST = timezone(timedelta(hours=5, minutes=30))


def _to_ist_str(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(IST).isoformat()


# Use as a field type in Pydantic models: ISTDatetime or ISTDatetime | None
# Datetimes stored in MongoDB as UTC are returned to the client as IST (+05:30).
ISTDatetime = Annotated[datetime, PlainSerializer(_to_ist_str, return_type=str, when_used="json")]
