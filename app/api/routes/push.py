from fastapi import APIRouter, Depends, status
from pydantic import BaseModel

from app.core.auth import get_current_user
from app.core.config import settings
from app.db.client import delete_push_subscription, save_push_subscription

router = APIRouter()


class PushKeys(BaseModel):
    p256dh: str
    auth: str


class PushSubscriptionRequest(BaseModel):
    endpoint: str
    keys: PushKeys


@router.get("/vapid-public-key")
async def vapid_public_key() -> dict:
    return {"public_key": settings.vapid_public_key}


@router.post("/subscribe", status_code=status.HTTP_201_CREATED)
async def subscribe(
    body: PushSubscriptionRequest,
    current_user: dict = Depends(get_current_user),
) -> dict:
    sub = {
        "endpoint": body.endpoint,
        "keys": {"p256dh": body.keys.p256dh, "auth": body.keys.auth},
    }
    await save_push_subscription(str(current_user["_id"]), sub)
    return {"ok": True}


@router.delete("/unsubscribe", status_code=status.HTTP_200_OK)
async def unsubscribe(
    body: PushSubscriptionRequest,
    current_user: dict = Depends(get_current_user),
) -> dict:
    await delete_push_subscription(body.endpoint)
    return {"ok": True}
