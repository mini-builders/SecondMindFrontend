import asyncio
import base64
import json
from functools import lru_cache, partial

import py_vapid
from pywebpush import webpush, WebPushException

from app.core.config import settings
from app.core.logger import get_logger
from app.db.client import delete_push_subscription

logger = get_logger(__name__)


@lru_cache(maxsize=1)
def _get_vapid() -> py_vapid.Vapid02:
    pem = base64.urlsafe_b64decode(settings.vapid_private_key + "==")
    return py_vapid.Vapid.from_pem(pem)


def _vapid_claims() -> dict:
    return {"sub": f"mailto:{settings.vapid_claim_email}"}


def _send_sync(subscription: dict, payload: str) -> None:
    webpush(
        subscription_info=subscription,
        data=payload,
        vapid_private_key=_get_vapid(),
        vapid_claims=_vapid_claims(),
    )


async def send_push(subscription: dict, title: str, body: str, data: dict | None = None) -> bool:
    payload = json.dumps({"title": title, "body": body, **({"data": data} if data else {})})
    loop = asyncio.get_event_loop()
    try:
        await loop.run_in_executor(None, partial(_send_sync, subscription, payload))
        return True
    except WebPushException as exc:
        status = exc.response.status_code if exc.response else None
        logger.warning("Push failed | endpoint=%s | status=%s", subscription.get("endpoint", "")[:60], status)
        if status in (404, 410):
            await delete_push_subscription(subscription.get("endpoint", ""))
        return False
    except Exception as exc:
        logger.error("Push error: %s", exc)
        return False
