import logging

from fastapi import APIRouter
from starlette.concurrency import run_in_threadpool

from src.apps.public_api.schemas.agent import AgentChatRequest, AgentChatResponse, AgentSourceOut, AgentStepOut
from src.core.errors import InternalServerError, ValidationError
from src.services.agent.agent import AgentService

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Agent"])

agent_service = AgentService()


@router.post("/agent/chat", response_model=AgentChatResponse)
async def agent_chat(payload: AgentChatRequest) -> AgentChatResponse:
    if not payload.message or not payload.message.strip():
        raise ValidationError("message cannot be empty")

    try:
        result = await run_in_threadpool(agent_service.chat, payload.message, payload.top_k)
    except ValueError as e:
        raise ValidationError(str(e)) from e
    except Exception as e:
        logger.error(f"Unexpected error in agent chat: {e}")
        raise InternalServerError("Agent failed to produce a response") from e

    return AgentChatResponse(
        answer=result.answer,
        used_retrieval=result.used_retrieval,
        routing_failed=result.routing_failed,
        steps=[AgentStepOut.model_validate(step, from_attributes=True) for step in result.steps],
        sources=[AgentSourceOut.model_validate(chunk, from_attributes=True) for chunk in result.sources],
    )
