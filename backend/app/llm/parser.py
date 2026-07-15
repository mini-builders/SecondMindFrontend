import json
from datetime import datetime, timezone, timedelta

from groq import AsyncGroq

from app.core.config import settings
from app.core.logger import get_logger
from app.llm.prompts import (
    TASK_EXTRACTION_SYSTEM_PROMPT,
    INTENT_ROUTER_SYSTEM_PROMPT,
    build_user_message,
)

logger = get_logger(__name__)

_IST = timezone(timedelta(hours=5, minutes=30))


async def route_intent(client: AsyncGroq, text: str) -> str:
    """Classify the user's input into an intent."""
    response = await client.chat.completions.create(
        model=settings.groq_model,
        messages=[
            {"role": "system", "content": INTENT_ROUTER_SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ],
        response_format={"type": "json_object"},
        temperature=0.1,
    )
    raw_content = response.choices[0].message.content
    try:
        data = json.loads(raw_content)
        return data.get("intent", "CREATE_TASK")
    except json.JSONDecodeError:
        return "CREATE_TASK"


async def extract_task_from_text(client: AsyncGroq, text: str) -> dict:
    """Send user text to the LLM and return the extracted task as a raw dict."""
    current_datetime = datetime.now(_IST).strftime("%Y-%m-%dT%H:%M:%S IST")
    user_message = build_user_message(text, current_datetime)

    logger.debug("Sending to Groq | model=%s | text=%s", settings.groq_model, text)

    response = await client.chat.completions.create(
        model=settings.groq_model,
        messages=[
            {"role": "system", "content": TASK_EXTRACTION_SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        response_format={"type": "json_object"},
        temperature=0.1,
    )

    raw_content = response.choices[0].message.content
    logger.debug("LLM response: %s", raw_content)

    try:
        return json.loads(raw_content)
    except json.JSONDecodeError as exc:
        logger.error("LLM returned invalid JSON: %s | raw=%s", exc, raw_content)
        raise ValueError("LLM returned malformed JSON") from exc
