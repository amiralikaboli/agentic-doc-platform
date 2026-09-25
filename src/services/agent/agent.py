import json
import logging
from dataclasses import dataclass, field
from typing import Any

from src.services.agent.tools import ToolExecutionError, ToolResult, ToolRegistry, RetrievalTool
from src.services.llm import get_llm_client

logger = logging.getLogger(__name__)

PLANNING_SYSTEM_PROMPT = """
You are the planning step of a document-assistant agent.
You have the following tools available:
{tools}

Given a single user message, decide which tools (if any) need to run, in
order, to gather what's needed to answer it. Tools run in the order you list
them; later tools do not currently see earlier tools' output, so only chain
tools that can each be resolved from the user's message alone.

Respond with ONLY a JSON array, with exactly this shape:
[
    {{"tool_name": "<tool name>", "arguments": <JSON object>}},
    ...
]

Return an empty array [] when the message can be answered without any tool.
Do not invent tool names. Use each tool's argument schema exactly.
"""

ANSWER_SYSTEM_PROMPT = (
    "You are a helpful document assistant. "
    "If tool outputs are provided, base your answer on them. If they report no results or do not "
    "contain enough information, say so instead of guessing. "
    "When a tool output contains numbered passages such as [1], [2], cite them inline. "
    "If no tool outputs are provided, answer the user's message directly."
)


def build_answer_messages(message: str, tool_outputs: list[tuple[str, str]]) -> list[dict[str, str]]:
    """Messages for the agent's final answer, given (tool_name, output) pairs."""
    if tool_outputs:
        blocks = "\n\n".join(f"Output of {name}:\n{output}" for name, output in tool_outputs)
        user_prompt = f"Tool outputs:\n{blocks}\n\nUser message: {message}"
    else:
        user_prompt = message

    return [
        {"role": "system", "content": ANSWER_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]


@dataclass
class AgentStep:
    tool_name: str
    tool_input: str
    used: bool = False
    detail: str = ""


@dataclass
class AgentResult:
    answer: str
    steps: list[AgentStep] = field(default_factory=list)


class AgentService:
    """Tool-registry-driven agent loop.

    Infrastructure dependencies are supplied by the composition root. The
    agent owns neither client construction nor tool discovery, and its loop
    is generic over whatever tools happen to be registered: adding a new
    tool means registering it with `tool_registry`, nothing here changes.
    """

    def __init__(self, tool_registry: ToolRegistry) -> None:
        self._tools = tool_registry
        self._llm_client = get_llm_client()

    def chat(self, message: str) -> AgentResult:
        if not message or not message.strip():
            raise ValueError("message cannot be empty")

        plan = self._plan(message)
        steps: list[AgentStep] = []
        tool_outputs: list[tuple[str, str]] = []

        for tool_name, arguments in plan:
            arguments = dict(arguments)
            tool = self._tools.get(tool_name)

            try:
                parsed_arguments = tool.parse_arguments(arguments)
                result = tool.execute(parsed_arguments)
                if not isinstance(result, ToolResult):
                    raise ToolExecutionError(f"Tool '{tool.name}' returned an invalid result")

                used = bool(result.content and result.content.strip())
                tool_outputs.append((tool.name, result.content if used else "(no results)"))

                steps.append(
                    AgentStep(
                        tool_name=tool.name,
                        tool_input=json.dumps(arguments),
                        used=used,
                        detail=tool.result_detail(result),
                    )
                )
            except Exception as e:
                logger.warning("AgentService: tool '%s' failed: %s", tool_name, e)
                steps.append(
                    AgentStep(
                        tool_name=tool_name,
                        tool_input=json.dumps(arguments),
                        used=False,
                        detail=str(e),
                    )
                )

        answer = self._llm_client.generate(build_answer_messages(message, tool_outputs))
        return AgentResult(answer=answer, steps=steps)

    def _plan(self, message: str) -> list[tuple[str, dict[str, Any]]]:
        """Ask the LLM which registered tools (if any) to run, in order.

        Fully generic over the tool registry's contents: the prompt is built
        from `self._tools.prompt_spec()` and every entry is validated against
        `self._tools.get(...)`, so newly-registered tools are pickable by the
        planner and dispatchable here with no code change.
        """
        system_prompt = PLANNING_SYSTEM_PROMPT.format(tools=self._tools.prompt_spec())
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": message},
        ]

        try:
            raw = self._llm_client.generate(messages, max_tokens=300, temperature=0.0)
        except Exception as e:
            logger.error("AgentService: planning LLM call failed: %s", e)
            return []

        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as e:
            logger.warning("AgentService: invalid planning response: %s; raw=%r", e, raw)
            return []

        if not isinstance(payload, list):
            logger.warning("AgentService: planning response must be a JSON array; raw=%r", raw)
            return []

        plan: list[tuple[str, dict[str, Any]]] = []
        for entry in payload:
            if not isinstance(entry, dict):
                logger.warning("AgentService: skipping malformed plan entry: %r", entry)
                continue

            tool_name = entry.get("tool_name")
            arguments = entry.get("arguments") or {}
            if not isinstance(tool_name, str) or not isinstance(arguments, dict):
                logger.warning("AgentService: skipping malformed plan entry: %r", entry)
                continue

            try:
                self._tools.get(tool_name)
            except ToolExecutionError:
                logger.warning("AgentService: skipping unknown tool in plan: %s", tool_name)
                continue

            plan.append((tool_name, arguments))

        return plan


_agent_service = AgentService(
    tool_registry=ToolRegistry([
        RetrievalTool()
    ])
)


def get_agent_service() -> AgentService:
    return _agent_service
