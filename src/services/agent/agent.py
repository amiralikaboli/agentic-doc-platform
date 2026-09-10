import json
import logging
from dataclasses import dataclass, field
from typing import List

logger = logging.getLogger(__name__)

ROUTING_SYSTEM_PROMPT = """
You are the routing step of a document-assistant agent. You have exactly one tool available:

retrieve_documents(query: str) -> relevant passages from a knowledge base of previously ingested documents.

Given a single user message, decide whether answering it requires calling that tool. Respond with ONLY a JSON object, no other text, in exactly this shape:
{
    needs_retrieval: true | false, 
    search_query: <str> | null
}

Set needs_retrieval to false for greetings, small talk, or anything answerable without looking anything up. Set it to true for anything that asks about, or requires, content the documents might contain.
"""


@dataclass
class AgentStep:
    tool_name: str
    tool_input: str
    succeeded: bool
    detail: str = ""


@dataclass
class AgentResult:
    answer: str
    used_retrieval: bool
    steps: List[AgentStep] = field(default_factory=list)
    sources: List = field(default_factory=list)


class AgentService:
    """
    Minimal single-tool agent loop (BB10):

      1. Decide whether the message needs the retrieval tool (routing step).
      2. If so, call it — a failed or malformed tool call is caught and the agent
         degrades gracefully instead of crashing the request.
      3. Generate a final answer, grounded in whatever context (if any) was retrieved.

    The LLM client and retrieval client are injectable so this can be unit-tested
    without a live gRPC server or LLM backend.
    """

    def __init__(self):
        from src.services.llm.client import get_llm_client
        self.llm_client = get_llm_client()

        from src.apps.public_api.grpc_client import get_retrieval_client
        self.retrieval_client = get_retrieval_client()

        from services.llm.service import GenerationService
        self.generation_service = GenerationService()

    def chat(self, message: str, top_k: int = 5) -> AgentResult:
        if not message or not message.strip():
            raise ValueError("message cannot be empty")

        needs_retrieval, search_query = self._decide(message)

        steps: List[AgentStep] = []
        chunks: List = []
        retrieval_failed = False

        if needs_retrieval:
            try:
                chunks = self.retrieval_client.search(search_query, top_k=top_k)
                steps.append(AgentStep(
                    tool_name="retrieval",
                    tool_input=search_query,
                    succeeded=True,
                    detail=f"{len(chunks)} chunk(s) retrieved",
                ))
            except Exception as e:
                logger.warning(f"AgentService: retrieval tool failed, answering without context: {e}")
                steps.append(AgentStep(
                    tool_name="retrieval",
                    tool_input=search_query,
                    succeeded=False,
                    detail=str(e),
                ))
                retrieval_failed = True

        answer = self._generate_answer(message, chunks, retrieval_failed)

        return AgentResult(
            answer=answer,
            used_retrieval=needs_retrieval,
            steps=steps,
            sources=chunks,
        )

    def _decide(self, message: str) -> tuple[bool, str]:
        messages = [
            {"role": "system", "content": ROUTING_SYSTEM_PROMPT},
            {"role": "user", "content": message},
        ]
        try:
            raw = self.llm_client.generate(messages, max_tokens=200, temperature=0.0)
        except Exception as e:
            logger.error(f"AgentService: routing LLM call failed, defaulting to no retrieval: {e}")
            return False, message

        try:
            payload = json.loads(raw)
            return payload["needs_retrieval"], payload["search_query"]
        except (ValueError, json.JSONDecodeError, TypeError, AttributeError) as e:
            logger.warning(
                f"AgentService: could not parse routing decision ({e}); defaulting to no retrieval. raw={raw!r}"
            )
            return False, message

    def _generate_answer(self, message: str, chunks: List, retrieval_failed: bool) -> str:
        contents = [chunk.content for chunk in chunks]
        answer = self.generation_service.generate(message, contents)
        if retrieval_failed:
            answer += (
                "\n\n(Note: document search was unavailable for this response, "
                "so it isn't grounded in retrieved context.)"
            )
        return answer
