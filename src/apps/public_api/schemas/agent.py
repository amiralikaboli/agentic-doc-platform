
from pydantic import BaseModel, Field


class AgentChatRequest(BaseModel):
    message: str = Field(min_length=1)
    top_k: int = Field(default=5, ge=1, le=20)


class AgentStepOut(BaseModel):
    tool_name: str
    tool_input: str
    succeeded: bool
    detail: str = ""


class AgentSourceOut(BaseModel):
    id: str
    document_id: str
    content: str
    chunk_index: int
    score: float


class AgentChatResponse(BaseModel):
    answer: str
    used_retrieval: bool
    steps: list[AgentStepOut]
    sources: list[AgentSourceOut]
