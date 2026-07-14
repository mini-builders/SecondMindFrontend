from contextlib import asynccontextmanager
from pathlib import Path

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.responses import Response
from starlette.staticfiles import StaticFiles as _StarletteStaticFiles

from app.api.router import api_router
from app.api.routes.whatsapp import router as whatsapp_router
from app.core.config import settings
from app.core.logger import get_logger
from app.db.client import connect as db_connect, disconnect as db_disconnect
from app.workers.notification_worker import run_push_worker

logger = get_logger(__name__)

_scheduler = AsyncIOScheduler()


class NoCacheStaticFiles(_StarletteStaticFiles):
    """StaticFiles that disables browser caching — used in development."""
    async def get_response(self, path: str, scope) -> Response:
        response = await super().get_response(path, scope)
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    await db_connect()
    logger.info("MongoDB connected | uri=%s", settings.mongodb_uri)
    _scheduler.add_job(run_push_worker, "interval", seconds=60, id="push_worker")
    _scheduler.start()
    logger.info("Push worker scheduled (60 s interval)")
    yield
    _scheduler.shutdown(wait=False)
    await db_disconnect()
    logger.info("MongoDB disconnected")


def create_app() -> FastAPI:
    app = FastAPI(
        title="SecondMind",
        description="Intelligent task parsing API — understands what you want to do.",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.include_router(api_router, prefix="/api/v1")
    app.include_router(whatsapp_router)

    @app.get("/health", tags=["Health"])
    async def health_check() -> dict:
        return {"status": "ok", "env": settings.app_env}

    @app.get("/.well-known/appspecific/com.chrome.devtools.json", include_in_schema=False)
    async def chrome_devtools_json() -> JSONResponse:
        return JSONResponse({})

    static_dir = Path(__file__).parent.parent / "static"
    static_dir.mkdir(exist_ok=True)

    static_cls = NoCacheStaticFiles if settings.app_env == "development" else StaticFiles
    app.mount("/", static_cls(directory=static_dir, html=True), name="static")

    return app


app = create_app()
