from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.core.auth import get_current_user
from app.core.logger import get_logger
from app.db.client import (
    archive_completed_tasks,
    get_notifications_collection,
    get_pending_user_tasks,
    get_tasks_collection,
    get_user_tasks,
    get_users_collection,
)
from app.exceptions import TaskConflictError
from app.models.request import ParseRequest
from app.models.response import ParseResponse
from app.models.task import TaskDocument
from app.services.parser_service import parse_task

logger = get_logger(__name__)

router = APIRouter()


@router.get("", response_model=list[TaskDocument])
async def list_tasks_route(
    current_user: dict = Depends(get_current_user),
) -> list[TaskDocument]:
    user_id = str(current_user["_id"])
    docs = await get_user_tasks(user_id)
    return [TaskDocument(**doc) for doc in docs]


@router.post("/parse", response_model=ParseResponse, status_code=status.HTTP_201_CREATED)
async def parse_task_route(
    request: ParseRequest,
    current_user: dict = Depends(get_current_user),
) -> ParseResponse:
    user_id = str(current_user["_id"])
    logger.info("Incoming parse request | user_id=%s | text=%s", user_id, request.text)

    try:
        return await parse_task(
            request.text,
            user_id=user_id,
            category=request.category,
            priority=request.priority,
        )
    except TaskConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "warning": "You already have a task scheduled around this time.",
                "conflicting_task_id": exc.conflicting_task_id,
                "conflicting_task_title": exc.conflicting_task_title,
            },
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except Exception as exc:
        logger.error("Unexpected error: %s", exc, exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to process task.")


class CreateCategoryRequest(BaseModel):
    name: str


@router.get("/categories", response_model=list[str])
async def list_categories_route(
    current_user: dict = Depends(get_current_user),
) -> list[str]:
    user_id = str(current_user["_id"])
    user = await get_users_collection().find_one({"_id": ObjectId(user_id)})
    custom = user.get("custom_categories", []) if user else []
    defaults = ["work", "health", "shopping", "financial", "social", "home", "learning", "travel", "entertainment"]
    all_cats = list(defaults)
    for c in custom:
        if c not in all_cats:
            all_cats.append(c)
    return all_cats


@router.post("/categories", response_model=list[str])
async def add_category_route(
    request: CreateCategoryRequest,
    current_user: dict = Depends(get_current_user),
) -> list[str]:
    user_id = str(current_user["_id"])
    cat_name = request.name.strip().lower()
    if not cat_name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Category name cannot be empty.")
    defaults = ["work", "health", "shopping", "financial", "social", "home", "learning", "travel", "entertainment"]
    if cat_name in defaults:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Category already exists.")
    user = await get_users_collection().find_one({"_id": ObjectId(user_id)})
    custom = user.get("custom_categories", []) if user else []
    if cat_name not in custom:
        custom.append(cat_name)
        await get_users_collection().update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"custom_categories": custom}},
        )
    return list(defaults) + custom


@router.get("/pending", response_model=list[TaskDocument])
async def list_pending_tasks_route(
    current_user: dict = Depends(get_current_user),
) -> list[TaskDocument]:
    user_id = str(current_user["_id"])
    docs = await get_pending_user_tasks(user_id)
    return [TaskDocument(**doc) for doc in docs]


@router.delete("/completed", status_code=status.HTTP_200_OK)
async def clear_completed_tasks_route(
    current_user: dict = Depends(get_current_user),
) -> dict:
    user_id = str(current_user["_id"])
    archived = await archive_completed_tasks(user_id)
    logger.info("Archived completed tasks | user_id=%s | count=%d", user_id, archived)
    return {"archived": archived}


class UpdateTaskRequest(BaseModel):
    severity: str | None = None
    category: str | None = None
    title: str | None = None


@router.patch("/{task_id}", response_model=TaskDocument)
async def update_task_route(
    task_id: str,
    request: UpdateTaskRequest,
    current_user: dict = Depends(get_current_user),
) -> TaskDocument:
    user_id = str(current_user["_id"])
    tasks_collection = get_tasks_collection()

    try:
        obj_id = ObjectId(task_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid task ID format.")

    task = await tasks_collection.find_one({"_id": obj_id, "user_id": user_id})
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found.")

    update_data = {}
    if request.severity is not None:
        if request.severity not in ["high", "medium", "low"]:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Severity must be 'high', 'medium', or 'low'.")
        update_data["severity"] = request.severity

    if request.category is not None:
        update_data["category"] = request.category
        notifications_collection = get_notifications_collection()
        await notifications_collection.update_many({"task_id": task_id}, {"$set": {"category": request.category}})

    if request.title is not None:
        update_data["title"] = request.title
        notifications_collection = get_notifications_collection()
        await notifications_collection.update_many({"task_id": task_id}, {"$set": {"task_title": request.title}})

    if update_data:
        update_data["updated_at"] = datetime.now(timezone.utc)
        await tasks_collection.update_one({"_id": obj_id}, {"$set": update_data})
        task = await tasks_collection.find_one({"_id": obj_id})

    return TaskDocument(**task)
