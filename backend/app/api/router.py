from fastapi import APIRouter

from app.api.routes.auth import router as auth_router
from app.api.routes.notifications import router as notifications_router
from app.api.routes.parser import router as parser_router
from app.api.routes.push import router as push_router
from app.api.routes.agent import router as agent_router

api_router = APIRouter()
api_router.include_router(auth_router, prefix="/auth", tags=["Auth"])
api_router.include_router(parser_router, prefix="/tasks", tags=["Tasks"])
api_router.include_router(notifications_router, prefix="/notifications", tags=["Notifications"])
api_router.include_router(push_router, prefix="/push", tags=["Push"])
api_router.include_router(agent_router, prefix="/agent", tags=["Agent"])
