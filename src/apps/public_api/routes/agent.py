import logging

from fastapi import APIRouter
from starlette.concurrency import run_in_threadpool

from src.apps.public_api.schemas.agent import AgentChatRequest, AgentChatResponse, AgentStepOut
from src.core.errors import InternalServerError, ValidationError
from src.services.agent import get_agent_service

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Agent"])


@router.post("/agent/chat", response_model=AgentChatResponse)
async def agent_chat(payload: AgentChatRequest) -> AgentChatResponse:
    if not payload.message or not payload.message.strip():
        raise ValidationError("message cannot be empty")

    agent_service = get_agent_service()
    try:
        result = await run_in_threadpool(agent_service.chat, payload.message)
    except ValueError as e:
        raise ValidationError(str(e)) from e
    except Exception as e:
        logger.error("Unexpected error in agent chat: %s", e)
        raise InternalServerError("Agent failed to produce a response") from e

    return AgentChatResponse(
        answer=result.answer,
        steps=[
            AgentStepOut(
                tool_name=step.tool_name,
                tool_input=step.tool_input,
                used=step.used,
                detail=step.detail,
            )
            for step in result.steps
        ]
    )
