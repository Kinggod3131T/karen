from typing import Any, Literal

from pydantic import BaseModel, Field

from services.core.app.schemas import PlannedAction


class CodingTaskRequest(BaseModel):
    path: str = "karen"
    task: str = Field(min_length=1, max_length=20_000)
    model: str | None = None
    max_context_files: int = Field(default=6, ge=1, le=12)


class CodingPlan(BaseModel):
    summary: str = Field(min_length=1)
    actions: list[PlannedAction] = Field(
        min_length=1,
        max_length=12,
    )


class VerificationResult(BaseModel):
    name: str
    command: list[str]
    return_code: int
    stdout: str
    stderr: str
    passed: bool
    timed_out: bool = False


class ReviewResult(BaseModel):
    verdict: Literal["approved", "changes_requested"]
    summary: str = Field(min_length=1)
    risks: list[str] = Field(default_factory=list, max_length=10)
    suggested_fixes: list[str] = Field(
        default_factory=list,
        max_length=10,
    )


class CodingTaskRecord(BaseModel):
    id: str
    project_path: str
    task: str
    model: str

    status: Literal[
        "pending",
        "running",
        "completed",
        "needs_review",
        "rejected",
        "failed",
    ] = "pending"

    context_files: list[str] = Field(default_factory=list)
    plan: CodingPlan

    checkpoint: str | None = None
    action_results: list[dict[str, Any]] = Field(
        default_factory=list
    )
    verification_results: list[VerificationResult] = Field(
        default_factory=list
    )
    review: ReviewResult | None = None

    created_at: str
    updated_at: str
    error: str | None = None
