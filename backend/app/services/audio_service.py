"""
app/services/audio_service.py

Downloads WhatsApp voice notes and transcribes them using Groq's Whisper API.
"""
import httpx

from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger(__name__)

_GRAPH_BASE = "https://graph.facebook.com/v20.0"


async def download_whatsapp_media(media_id: str) -> bytes:
    """Download a media file from WhatsApp servers using the media ID."""
    headers = {"Authorization": f"Bearer {settings.whatsapp_access_token}"}

    async with httpx.AsyncClient() as client:
        # Step 1: Get the media URL
        meta_resp = await client.get(
            f"{_GRAPH_BASE}/{media_id}", headers=headers, timeout=10
        )
        meta_resp.raise_for_status()
        media_url = meta_resp.json().get("url")

        if not media_url:
            raise ValueError(f"No URL returned for media_id={media_id}")

        # Step 2: Download the actual file
        file_resp = await client.get(media_url, headers=headers, timeout=30)
        file_resp.raise_for_status()
        return file_resp.content


async def transcribe_audio(audio_bytes: bytes, filename: str = "voice.ogg") -> str:
    """Transcribe audio bytes using Groq's Whisper API."""
    from groq import AsyncGroq

    client = AsyncGroq(api_key=settings.groq_api_key)

    transcription = await client.audio.transcriptions.create(
        file=(filename, audio_bytes),
        model="whisper-large-v3",
        language="en",
    )

    text = transcription.text.strip()
    logger.info("Transcription complete | length=%d | text=%s", len(text), text[:100])
    return text
