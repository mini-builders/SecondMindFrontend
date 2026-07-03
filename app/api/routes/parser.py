from fastapi import APIRouter, Depends, HTTPException, status

from app.core.auth import get_current_user
from app.core.logger import get_logger
from app.exceptions import TaskConflictError
from app.models.request import ParseRequest
from app.models.response import ParseResponse
from app.services.parser_service import parse_task

logger = get_logger(__name__)

router = APIRouter()


@router.post("/parse", response_model=ParseResponse, status_code=status.HTTP_201_CREATED)
async def parse_task_route(
    request: ParseRequest,
    current_user: dict = Depends(get_current_user),
) -> ParseResponse:
    user_id = str(current_user["_id"])
    logger.info("Incoming parse request | user_id=%s | text=%s", user_id, request.text)

    try:
        return await parse_task(request.text, user_id=user_id)
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
