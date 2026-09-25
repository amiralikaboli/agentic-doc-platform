from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Protocol

from threading import Lock

from src.services.agent.tools import ToolExecutionError, ToolRegistry, ToolResult

logger = logging.getLogger(__name__)


class LLMGenerator(Protocol):
    def generate(
        self,
        messages: list[dict[str, str]],
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> str:
        ...


ROUTING_SYSTEM_PROMPT = """
You are the routing step of a document-assistant agent.
You have the following tools available:
{tools}

Given a single user message, decide whether to call a tool.
Respond with ONLY a JSON object, with exactly this shape:
{{
    "tool_name": "<tool name>" | null,
    "arguments": <JSON object> | null
}}

Choose null when the message can be answered without any available tool.
Do not invent tool names. Use the tool's argument schema exactly.
"""


class GenerationPort(Protocol):
    def generate(self, query: str, chunks: list[str]) -> str:
        ...


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
    steps: list[AgentStep] = field(default_factory=list)
    sources: list[Any] = field(default_factory=list)


class AgentService:
    """Small, tool-registry-based agent loop for BB10.

    Infrastructure dependencies are supplied by the composition root. The agent
    owns neither client construction nor tool discovery.
    """

    def __init__(
        self,
        *,
        llm_client: LLMGenerator,
        generation_service: GenerationPort,
        tool_registry: ToolRegistry,
    ) -> None:
        self._llm_client = llm_client
        self._generation_service = generation_service
        self._tools = tool_registry

    def chat(self, message: str, top_k: int = 5) -> AgentResult:
        if not message or not message.strip():
            raise ValueError("message cannot be empty")

        tool_name, arguments = self._decide(message)
        steps: list[AgentStep] = []
        tool_context: list[str] = []
        sources: list[Any] = []
        tool_failed = False

        if tool_name is not None:
            arguments = dict(arguments or {})
            tool = self._tools.get(tool_name)
            if "top_k" in tool.input_model.model_fields:
                arguments.setdefault("top_k", top_k)

            try:
                parsed_arguments = tool.parse_arguments(arguments)
                result = tool.execute(parsed_arguments)
                if not isinstance(result, ToolResult):
                    raise ToolExecutionError(f"Tool '{tool.name}' returned an invalid result")
                tool_context.append(result.content)
                sources.extend(result.metadata.get("sources", []))
                steps.append(
                    AgentStep(
                        tool_name=tool.name,
                        tool_input=json.dumps(arguments),
                        succeeded=True,
                        detail=tool.result_detail(result),
                    )
                )
            except Exception as e:
                logger.warning("AgentService: tool '%s' failed: %s", tool_name, e)
                steps.append(
                    AgentStep(
                        tool_name=tool_name,
                        tool_input=json.dumps(arguments),
                        succeeded=False,
                        detail=str(e),
                    )
                )
                tool_failed = True

        answer = self._generate_answer(message, tool_context, tool_failed)
        return AgentResult(
            answer=answer,
            used_retrieval=tool_name == "retrieve_documents",
            steps=steps,
            sources=sources,
        )

    def _decide(self, message: str) -> tuple[str | None, dict[str, Any] | None]:
        system_prompt = ROUTING_SYSTEM_PROMPT.format(tools=self._tools.prompt_spec())
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": message},
        ]

        try:
            raw = self._llm_client.generate(messages, max_tokens=200, temperature=0.0)
        except Exception as e:
            logger.error("AgentService: routing LLM call failed: %s", e)
            return None, None

        try:
            payload = json.loads(raw)
            if not isinstance(payload, dict):
                raise ValueError("routing response must be a JSON object")
            tool_name = payload.get("tool_name")
            arguments = payload.get("arguments")
            if tool_name is not None and not isinstance(tool_name, str):
                raise ValueError("tool_name must be a string or null")
            if arguments is not None and not isinstance(arguments, dict):
                raise ValueError("arguments must be an object or null")
            if tool_name is not None:
                self._tools.get(tool_name)
            return tool_name, arguments
        except (json.JSONDecodeError, TypeError, ValueError, ToolExecutionError) as e:
            logger.warning("AgentService: invalid routing decision: %s; raw=%r", e, raw)
            return None, None

    def _generate_answer(self, message: str, tool_context: list[str], tool_failed: bool) -> str:
        answer = self._generation_service.generate(message, tool_context)
        if tool_failed:
            answer += (
                "\n\n(Note: a requested tool was unavailable for this response, "
                "so the answer may not be grounded in retrieved context.)"
            )
        return answer


_agent_service: AgentService | None = None
_agent_service_lock = Lock()


def get_agent_service() -> AgentService:
    """Return the process-wide AgentService singleton.

    Construction stays inside the service layer so FastAPI startup/application
    wiring does not need to know how the agent and its tools are assembled.
    Tests can still instantiate AgentService directly with fakes.
    """
    global _agent_service

    if _agent_service is None:
        with _agent_service_lock:
            if _agent_service is None:
                from src.apps.public_api.grpc_client import get_retrieval_client
                from src.services.llm.client import get_llm_client
                from src.services.agent.tools import ToolRegistry
                from src.services.agent.tools.retrieval import RetrievalTool
                from src.services.llm.service import get_generation_service

                _agent_service = AgentService(
                    llm_client=get_llm_client(),
                    generation_service=get_generation_service(),
                    tool_registry=ToolRegistry(
                        [RetrievalTool(get_retrieval_client())]
                    ),
                )

    return _agent_service
