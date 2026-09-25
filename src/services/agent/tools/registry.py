from __future__ import annotations

from typing import Any

from src.services.agent.tools.base import BaseTool, ToolExecutionError


class ToolRegistry:
    """Owns the set of tools made available to one agent."""

    def __init__(self, tools: list[BaseTool[Any, Any]] | None = None) -> None:
        self._tools: dict[str, BaseTool[Any, Any]] = {}
        for tool in tools or []:
            self.register(tool)

    def register(self, tool: BaseTool[Any, Any]) -> None:
        if tool.name in self._tools:
            raise ValueError(f"Tool already registered: {tool.name}")
        self._tools[tool.name] = tool

    def get(self, name: str) -> BaseTool[Any, Any]:
        try:
            return self._tools[name]
        except KeyError as e:
            raise ToolExecutionError(f"Unknown tool: {name}") from e

    def list(self) -> list[BaseTool[Any, Any]]:
        return list(self._tools.values())

    def prompt_spec(self) -> str:
        tools = self.list()
        if not tools:
            return "(no tools available)"
        return "\n".join(tool.prompt_spec() for tool in tools)
