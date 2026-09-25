from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from src.apps.public_api.grpc_client import RetrievalClient
from src.services.agent.tools.base import BaseTool, ToolResult


class RetrievalToolInput(BaseModel):
    query: str = Field(min_length=1)
    top_k: int = Field(default=5, ge=1, le=20)


class RetrievalTool(BaseTool[RetrievalToolInput, ToolResult]):
    """Agent-facing wrapper around the internal retrieval service."""

    name = "retrieve_documents"
    description = (
        "Search the ingested document knowledge base and return relevant passages "
        "when the user's question requires document content."
    )
    input_model = RetrievalToolInput

    def __init__(self, client: RetrievalClient) -> None:
        self._client = client

    def execute(self, arguments: RetrievalToolInput) -> ToolResult:
        chunks = list(self._client.search(arguments.query, top_k=arguments.top_k).results)
        content = "\n\n".join(f"[{i + 1}] {chunk.content}" for i, chunk in enumerate(chunks))
        return ToolResult(content=content, metadata={"sources": chunks})

    def result_detail(self, result: ToolResult) -> str:
        return f"{len(result.metadata.get('sources', []))} chunk(s) retrieved"
