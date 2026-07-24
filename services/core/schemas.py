from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


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


class PlanRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=20_000)


class PlannedAction(BaseModel):
    action: Literal["create_directory", "write_file"]
    path: str = Field(min_length=1)
    content: str | None = None
    reason: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_action_content(self) -> "PlannedAction":
        if self.action == "write_file" and self.content is None:
            raise ValueError("write_file requires content")

        return self


class ModelPlan(BaseModel):
    summary: str = Field(min_length=1)
    actions: list[PlannedAction] = Field(
        min_length=1,
        max_length=20,
    )


class ProposalRecord(BaseModel):
    id: str
    task: str
    summary: str
    status: Literal[
        "pending",
        "executed",
        "rejected",
        "failed",
    ] = "pending"

    actions: list[PlannedAction]
    created_at: str
    results: list[dict[str, Any]] = Field(default_factory=list)
    error: str | None = None
