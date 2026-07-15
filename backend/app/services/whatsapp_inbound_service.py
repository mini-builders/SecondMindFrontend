"""
app/services/whatsapp_inbound_service.py

Processes inbound WhatsApp messages from Meta's webhook.
Handles button replies (done/snooze) and free-text task creation.
No HTTP/route knowledge here — called by the webhook route.
"""
from app.core.logger import get_logger
from app.db.client import get_user_by_whatsapp, mark_task_done, snooze_notification
from app.exceptions import TaskConflictError
from app.services import whatsapp_service
from app.services.parser_service import parse_task
from app.services.audio_service import download_whatsapp_media, transcribe_audio

logger = get_logger(__name__)


async def handle_payload(payload: dict) -> None:
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            for message in value.get("messages", []):
                await _dispatch(message)


async def _dispatch(message: dict) -> None:
    wa_id = message.get("from", "")
    user = await get_user_by_whatsapp(wa_id)
    if not user:
        logger.warning("WhatsApp message from unregistered number | wa_id=%s", wa_id)
        return

    user_id = str(user["_id"])
    msg_type = message.get("type")

    if msg_type == "interactive":
        await _handle_interactive(wa_id, user_id, message)
    elif msg_type == "text":
        await _handle_text(wa_id, user_id, message)
    elif msg_type == "audio":
        await _handle_audio(wa_id, user_id, message)


async def _handle_interactive(wa_id: str, user_id: str, message: dict) -> None:
    reply_id = message.get("interactive", {}).get("button_reply", {}).get("id", "")

    if reply_id.startswith("done:"):
        task_id = reply_id[5:]
        await mark_task_done(task_id, user_id)
        await whatsapp_service.send_text(wa_id, "✅ Done! Task marked complete.")
        logger.info("Task done via WhatsApp | task_id=%s | user_id=%s", task_id, user_id)

    elif reply_id.startswith("snooze10:"):
        task_id = reply_id[9:]
        await snooze_notification(task_id, user_id, 10)
        await whatsapp_service.send_text(wa_id, "😴 Snoozed for 10 minutes.")
        logger.info("Task snoozed via WhatsApp | task_id=%s | user_id=%s", task_id, user_id)


async def _handle_text(wa_id: str, user_id: str, message: dict) -> None:
    text = message.get("text", {}).get("body", "").strip()
    if not text:
        return

    try:
        result = await parse_task(text, user_id=user_id, category=None, priority=None)
        time_str = (
            result.scheduled_time.strftime("%d %b at %I:%M %p")
            if result.scheduled_time
            else "no specific time"
        )
        await whatsapp_service.send_text(
            wa_id,
            f"✅ Got it! Added: *{result.title}*\n📅 {time_str}",
        )
        logger.info("Task created via WhatsApp | user_id=%s | title=%s", user_id, result.title)

    except TaskConflictError as exc:
        await whatsapp_service.send_text(
            wa_id,
            f"🚫 Conflict! You already have *{exc.conflicting_task_title}* scheduled around that time. "
            f"Want a different time?",
        )

    except Exception as exc:
        logger.error("WhatsApp text handling failed | wa_id=%s | error=%s", wa_id, exc)
        await whatsapp_service.send_text(wa_id, "Sorry, I couldn't process that. Please try again.")


async def _handle_audio(wa_id: str, user_id: str, message: dict) -> None:
    """Handle incoming voice notes — download, transcribe, then parse as a task."""
    audio_info = message.get("audio", {})
    media_id = audio_info.get("id")

    if not media_id:
        logger.warning("Audio message missing media ID | wa_id=%s", wa_id)
        return

    try:
        await whatsapp_service.send_text(wa_id, "🎙️ Got your voice note — transcribing...")

        audio_bytes = await download_whatsapp_media(media_id)
        text = await transcribe_audio(audio_bytes)

        if not text:
            await whatsapp_service.send_text(wa_id, "Sorry, I couldn't understand that voice note. Try again?")
            return

        logger.info("Voice note transcribed | wa_id=%s | text=%s", wa_id, text[:80])

        result = await parse_task(text, user_id=user_id, category=None, priority=None)
        time_str = (
            result.scheduled_time.strftime("%d %b at %I:%M %p")
            if result.scheduled_time
            else "no specific time"
        )
        await whatsapp_service.send_text(
            wa_id,
            f"✅ Got it from your voice note!\n*{result.title}*\n📅 {time_str}",
        )
        logger.info("Task created via voice note | user_id=%s | title=%s", user_id, result.title)

    except TaskConflictError as exc:
        await whatsapp_service.send_text(
            wa_id,
            f"🚫 Conflict! You already have *{exc.conflicting_task_title}* scheduled around that time. "
            f"Want a different time?",
        )

    except Exception as exc:
        logger.error("Voice note handling failed | wa_id=%s | error=%s", wa_id, exc, exc_info=True)
        await whatsapp_service.send_text(wa_id, "Sorry, something went wrong with your voice note. Try typing it instead?")
