from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ValidationError

TInput = TypeVar("TInput", bound=BaseModel)
TOutput = TypeVar("TOutput", bound="ToolResult")


@dataclass(frozen=True)
class ToolResult:
    """Normalized tool observation passed back into the agent loop."""

    content: str
    metadata: dict[str, Any] = field(default_factory=dict)


class ToolExecutionError(Exception):
    """Raised when a tool cannot execute a request because its input is invalid or unavailable."""


class BaseTool(ABC, Generic[TInput, TOutput]):
    """Contract implemented by every capability exposed to an agent."""

    name: str
    description: str
    input_model: type[TInput]

    @abstractmethod
    def execute(self, arguments: TInput) -> TOutput:
        raise NotImplementedError

    def parse_arguments(self, raw_arguments: str | dict[str, Any]) -> TInput:
        try:
            payload = json.loads(raw_arguments) if isinstance(raw_arguments, str) else raw_arguments
        except json.JSONDecodeError as e:
            raise ToolExecutionError(f"Malformed JSON arguments for tool '{self.name}'") from e

        try:
            return self.input_model.model_validate(payload)
        except ValidationError as e:
            raise ToolExecutionError(
                f"Invalid arguments for tool '{self.name}': {e.errors(include_url=False)}"
            ) from e

    def result_detail(self, result: TOutput) -> str:
        return "tool succeeded"

    def prompt_spec(self) -> str:
        schema = self.input_model.model_json_schema()
        return (
            f"- {self.name}: {self.description}\n"
            f"  arguments_schema: {json.dumps(schema, separators=(',', ':'))}"
        )
