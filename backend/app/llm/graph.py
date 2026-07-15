import json
from datetime import datetime, timezone, timedelta
from typing import TypedDict, Optional, Literal

from langgraph.graph import StateGraph, START, END
from langchain_groq import ChatGroq

from app.core.config import settings
from app.llm.prompts import (
    INTENT_ROUTER_SYSTEM_PROMPT,
    TASK_EXTRACTION_SYSTEM_PROMPT,
    build_user_message,
)

_IST = timezone(timedelta(hours=5, minutes=30))

class AgentState(TypedDict):
    text: str
    intent: Optional[str]
    task_raw: Optional[dict]
    error: Optional[str]

def route_node(state: AgentState) -> AgentState:
    llm = ChatGroq(
        api_key=settings.groq_api_key,
        temperature=0.1, 
        model=settings.groq_model, 
        max_retries=2
    ).bind(response_format={"type": "json_object"})
    messages = [
        {"role": "system", "content": INTENT_ROUTER_SYSTEM_PROMPT},
        {"role": "user", "content": state["text"]}
    ]
    response = llm.invoke(messages)
    try:
        data = json.loads(response.content)
        intent = data.get("intent", "CREATE_TASK")
    except Exception:
        intent = "CREATE_TASK"
        
    return {"intent": intent}

def extract_node(state: AgentState) -> AgentState:
    llm = ChatGroq(
        api_key=settings.groq_api_key,
        temperature=0.1, 
        model=settings.groq_model, 
        max_retries=2
    ).bind(response_format={"type": "json_object"})
    current_datetime = datetime.now(_IST).strftime("%Y-%m-%dT%H:%M:%S IST")
    user_message = build_user_message(state["text"], current_datetime)
    
    messages = [
        {"role": "system", "content": TASK_EXTRACTION_SYSTEM_PROMPT},
        {"role": "user", "content": user_message}
    ]
    response = llm.invoke(messages)
    try:
        task_raw = json.loads(response.content)
        return {"task_raw": task_raw}
    except Exception as exc:
        return {"error": str(exc)}

def intent_router(state: AgentState) -> Literal["extract", "end"]:
    if state["intent"] == "CREATE_TASK":
        return "extract"
    return "end"

workflow = StateGraph(AgentState)
workflow.add_node("route", route_node)
workflow.add_node("extract", extract_node)

workflow.add_edge(START, "route")
workflow.add_conditional_edges("route", intent_router, {"extract": "extract", "end": END})
workflow.add_edge("extract", END)

agent_graph = workflow.compile()
