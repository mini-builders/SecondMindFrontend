from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.core.auth import get_current_user
from app.core.logger import get_logger
from app.services.parser_service import parse_task
from app.services.insights_service import get_user_insights
from app.db.client import get_tasks_collection
from app.exceptions import TaskConflictError

logger = get_logger(__name__)
router = APIRouter()

class AgentRequest(BaseModel):
    text: str

class AgentResponse(BaseModel):
    intent: str
    message: str
    data: dict | None = None

from app.llm.graph import agent_graph

@router.post("/chat", response_model=AgentResponse)
async def agent_chat_route(
    request: AgentRequest,
    current_user: dict = Depends(get_current_user),
):
    user_id = str(current_user["_id"])
    
    # Run the langgraph workflow
    final_state = await agent_graph.ainvoke({"text": request.text})
    
    intent = final_state.get("intent", "CREATE_TASK")
    
    if intent == "SHOW_INSIGHTS":
        insights = await get_user_insights(user_id)
        rate = insights["completion_rate_percent"]
        msg = (
            f"📊 Here are your insights:\n"
            f"• Total tasks: {insights['total_tasks']}\n"
            f"• Completed: {insights['completed_tasks']}\n"
            f"• Pending: {insights['scheduled_tasks']}\n"
            f"• This week: {insights['completed_this_week']} completed\n"
            f"• Completion rate: {rate}%\n"
            f"• Total reminders fired: {insights['total_notifications_fired']}"
        )
        return AgentResponse(intent=intent, message=msg, data=insights)
        
    elif intent == "MANAGE_TASK":
        return AgentResponse(
            intent=intent,
            message="You want to manage a task. Please use the dashboard buttons to mark tasks as done or snooze them for now."
        )
        
    else:  # CREATE_TASK
        if final_state.get("error"):
            return AgentResponse(intent=intent, message="Sorry, I couldn't understand that task.")
            
        task_raw = final_state.get("task_raw")
        if not task_raw:
            return AgentResponse(intent=intent, message="Sorry, I couldn't extract the task details.")
            
        try:
            result = await parse_task(request.text, task_raw, user_id=user_id)
            return AgentResponse(
                intent=intent,
                message=f"Got it! I scheduled '{result.title}'.",
                data=result.model_dump(by_alias=True)
            )
        except TaskConflictError as exc:
            return AgentResponse(
                intent=intent,
                message=f"Conflict! You already have '{exc.conflicting_task_title}' scheduled then.",
                data={"conflict": True}
            )
        except Exception as exc:
            logger.error("Agent creation error: %s", exc)
            return AgentResponse(
                intent=intent,
                message="Sorry, I couldn't understand that task."
            )
