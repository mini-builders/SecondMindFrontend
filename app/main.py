from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.router import api_router
from app.core.config import settings
from app.core.logger import get_logger
from app.db.client import connect as db_connect, disconnect as db_disconnect

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await db_connect()
    logger.info("MongoDB connected | uri=%s", settings.mongodb_uri)
    yield
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

    static_dir = Path(__file__).parent.parent / "static"
    static_dir.mkdir(exist_ok=True)
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

    @app.get("/health", tags=["Health"])
    async def health_check() -> dict:
        return {"status": "ok", "env": settings.app_env}

    return app


app = create_app()
