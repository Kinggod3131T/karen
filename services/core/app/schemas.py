from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=30_000)
    model: str | None = None


class ChatResponse(BaseModel):
    model: str
    response: str
    done: bool


class FilePathRequest(BaseModel):
    path: str = Field(min_length=1)


class FileWriteRequest(BaseModel):
    path: str = Field(min_length=1)
    content: str
    confirm: bool = False
