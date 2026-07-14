"""
app/api/routes/whatsapp.py

Webhook routes only — no business logic here, per SecondMind's layering rule.
Delegates everything to whatsapp_inbound_service.
"""
import hmac
import hashlib

from fastapi import APIRouter, BackgroundTasks, Request, Response

from app.core.config import settings
from app.services import whatsapp_inbound_service

router = APIRouter(prefix="/api/v1/whatsapp", tags=["whatsapp"])


def verify_signature(raw_body: bytes, signature_header: str) -> bool:
    if not signature_header:
        return False
    expected = hmac.new(settings.whatsapp_app_secret.encode(), raw_body, hashlib.sha256).hexdigest()
    received = signature_header.replace("sha256=", "")
    return hmac.compare_digest(expected, received)


@router.get("/webhook")
async def verify_webhook(request: Request):
    """Meta's one-time handshake when you save the webhook config."""
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    if mode == "subscribe" and token == settings.whatsapp_verify_token:
        return Response(content=challenge, media_type="text/plain")
    return Response(status_code=403)


@router.post("/webhook")
async def receive_webhook(request: Request, background_tasks: BackgroundTasks):
    """Every inbound message and delivery/read status lands here."""
    raw_body = await request.body()
    signature = request.headers.get("x-hub-signature-256", "")

    if not verify_signature(raw_body, signature):
        return Response(status_code=403)

    payload = await request.json()
    background_tasks.add_task(whatsapp_inbound_service.handle_payload, payload)

    # Return 200 immediately — processing happens in background.
    # Meta retries aggressively on non-200 or timeout causing duplicate tasks.
    return Response(status_code=200)
