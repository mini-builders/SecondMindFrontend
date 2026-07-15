"""
app/services/whatsapp_service.py

Outbound WhatsApp messaging via Meta's Cloud API.
No HTTP/route knowledge here, per SecondMind's existing layering rule —
this mirrors the shape of push_service.py.
"""
import httpx

from app.core.config import settings

_GRAPH_BASE = "https://graph.facebook.com/v20.0"


async def _post(payload: dict) -> dict:
    url = f"{_GRAPH_BASE}/{settings.whatsapp_phone_number_id}/messages"
    headers = {
        "Authorization": f"Bearer {settings.whatsapp_access_token}",
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient() as client:
        r = await client.post(url, headers=headers, json=payload, timeout=10)
        r.raise_for_status()
        return r.json()


async def send_text(to: str, body: str) -> dict:
    """Free-form text. Only valid within 24h of the user's last inbound message."""
    return await _post({
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": body},
    })


async def send_quick_reply(to: str, body: str, buttons: list[tuple[str, str]]) -> dict:
    """buttons: list of (id, label) tuples. WhatsApp allows max 3 per message."""
    return await _post({
        "messaging_product": "whatsapp",
        "to": to,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {"text": body},
            "action": {
                "buttons": [
                    {"type": "reply", "reply": {"id": bid, "title": label}}
                    for bid, label in buttons[:3]
                ]
            },
        },
    })


async def send_reminder(to: str, task_title: str, task_id: str) -> dict:
    """Standard reminder with Done/Snooze quick replies. Use only within the 24h window —
    otherwise use send_template_reminder below."""
    return await send_quick_reply(
        to,
        f"🔔 Reminder: {task_title}",
        [
            (f"done:{task_id}", "✅ Done"),
            (f"snooze10:{task_id}", "😴 Snooze 10 min"),
        ],
    )


async def send_template_reminder(to: str, task_title: str, template_name: str = "reminder_notification") -> dict:
    """Fallback for outside the 24h session window. Requires the template to be
    pre-approved in Meta Business Manager → WhatsApp Manager → Message Templates."""
    return await _post({
        "messaging_product": "whatsapp",
        "to": to,
        "type": "template",
        "template": {
            "name": template_name,
            "language": {"code": "en"},
            "components": [{
                "type": "body",
                "parameters": [{"type": "text", "text": task_title}],
            }],
        },
    })


async def send_conflict_rejection(to: str, existing_task_title: str, start: str, end: str) -> dict:
    return await send_text(
        to,
        f"🚫 Can't add that — you already have {existing_task_title} from {start} to {end}. "
        f"Want a different time?"
    )
