from fastapi import APIRouter

from app.api.routes.notifications import router as notifications_router
from app.api.routes.parser import router as parser_router

api_router = APIRouter()
api_router.include_router(parser_router, prefix="/tasks", tags=["Tasks"])
api_router.include_router(notifications_router, prefix="/notifications", tags=["Notifications"])
