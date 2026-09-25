from pydantic import BaseModel, Field


class AgentChatRequest(BaseModel):
    message: str = Field(min_length=1)


class AgentStepOut(BaseModel):
    tool_name: str
    tool_input: str
    used: bool = False
    detail: str = ""


class AgentChatResponse(BaseModel):
    answer: str
    steps: list[AgentStepOut]
