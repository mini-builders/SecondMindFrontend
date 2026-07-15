# SecondMind Runtime Architecture

The runtime architecture of SecondMind defines how requests and background jobs flow through the system during execution.

## 1. Application Startup & Lifespan
- The application boots up using `uvicorn app.main:app --reload`.
- **Lifespan Context**: When FastAPI starts, it triggers the `lifespan` event.
  - It establishes an asynchronous connection pool to **MongoDB**.
  - It initializes the **APScheduler**, adding the `push_worker` job to run every 60 seconds.
- The `StaticFiles` middleware binds the `static/` folder to the root URL `/`, serving the frontend.

## 2. Conversational Task Creation Flow (Web & WhatsApp)
When a user types "remind me to call Mom at 5pm":
1. **Ingestion**: The text arrives via the Frontend (`POST /api/v1/tasks/parse`) or WhatsApp Webhook.
2. **Intent Parsing**: The `groq` client calls the LLM with `TASK_EXTRACTION_SYSTEM_PROMPT`. The LLM identifies the intent, category, time, and severity.
3. **Conflict Detection**: The system checks if the new task overlaps with any existing `is_blocking = true` tasks (like meetings or deep work) and resolves accordingly.
4. **Persistence**: The structured task is saved to MongoDB as a `TaskDocument`, and a corresponding `NotificationDocument` is created for future scheduling.
5. **Response**: A confirmation is returned to the user via Web or WhatsApp.

## 3. Voice Note Flow (WhatsApp)
1. **Webhook Event**: The user sends an audio note. WhatsApp hits our webhook.
2. **Audio Fetch**: The backend downloads the media file.
3. **Transcription**: The audio is sent to a Speech-to-Text service to extract text.
4. **Integration**: The extracted text is passed to the standard **Conversational Task Creation Flow** (step 2 above).

## 4. Background Notification Loop
1. **Trigger**: Every 60 seconds, the `push_worker` fires.
2. **Polling**: Queries MongoDB for any `NotificationDocument` where `next_fire_at <= NOW()` and `status == active`.
3. **Suppression Check**: Checks if the user is currently engaged in an active "meeting" task. If so, low and medium severity notifications are deferred.
4. **Execution**: If clear to fire, it triggers an outbound WhatsApp message.
5. **State Update**: Updates the `fire_count` and calculates the next `retry_interval_minutes` based on the task's severity. If max retries are reached, it transitions to a terminal state (but is not deleted, keeping it for insights).
