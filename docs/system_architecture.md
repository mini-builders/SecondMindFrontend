# SecondMind System Architecture

SecondMind is a unified web application built using Python (FastAPI) and vanilla web technologies, designed to handle intelligent task parsing and notifications via an LLM.

## High-Level Components

### 1. Presentation Layer (Frontend)
- **Tech Stack**: Vanilla HTML, CSS, and JavaScript.
- **Serving**: Hosted directly by the backend from the `static/` directory using FastAPI's `StaticFiles`.
- **Key Files**: 
  - `index.html`: The main conversational interface.
  - `sw.js`: Service worker for local caching and offline capabilities.
  - `manifest.json`: PWA configuration.

### 2. Application Layer (Backend)
- **Framework**: FastAPI (Python 3).
- **Server**: Uvicorn (ASGI server).
- **Core Responsibilities**: 
  - Exposing REST APIs for the frontend under `/api/v1/`.
  - Handling external webhooks (WhatsApp).
  - Orchestrating LLM calls for task parsing.

### 3. Intelligence Layer (LLM)
- **Provider**: Groq API (`groq` python client).
- **Role**: Parses natural language from the user ("remind me to call Mom tomorrow") into structured JSON objects (Task, Category, Severity, Scheduled Time) using carefully crafted system prompts located in `app/llm/prompts.py`.

### 4. Persistence Layer (Database)
- **Database**: MongoDB.
- **Driver**: Motor (Asynchronous Python driver for MongoDB).
- **Models (Pydantic)**:
  - `TaskDocument`: Stores the extracted user intents and metadata.
  - `NotificationDocument`: Stores scheduled reminder details.
  - `User`: Stores user preferences and verification states.

### 5. Background Processing (Scheduler)
- **Engine**: APScheduler (AsyncIOScheduler).
- **Role**: Runs a periodic job (`push_worker` running every 60 seconds) that scans the `NotificationDocument` collection for tasks that are due to trigger, handling retries (based on severity) and sending notifications to the WhatsApp integration.

## External Integrations
- **WhatsApp Webhook**: Receives messages and voice notes for task creation, and sends outbound reminders to the user when tasks are due.
- **Speech-to-Text**: Processing incoming WhatsApp voice notes into text for the LLM.
