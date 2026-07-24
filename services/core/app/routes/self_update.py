from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from services.core.app.project.scanner import scan_project
from services.core.app.project.schemas import ProjectScanRequest
from services.core.app.security.git_tools import (
    commit_staged,
    repository_status,
    stage_paths,
)
from services.core.app.workflow.planner import build_coding_plan
from services.core.app.workflow.schemas import (
    CodingTaskRecord,
    CodingTaskRequest,
)
from services.core.app.workflow.store import (
    load_task,
    save_task,
)


router = APIRouter(
    prefix="/self-update",
    tags=["Self update"],
)


class SelfUpdateRequest(BaseModel):
    task: str = Field(min_length=1, max_length=20_000)
    model: str | None = None
    max_context_files: int = Field(default=8, ge=1, le=12)


class FinalizeSelfUpdateRequest(BaseModel):
    confirm: bool = False
    message: str | None = Field(default=None, max_length=200)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _assert_clean_repository() -> None:
    result = repository_status("karen")
    lines = result["status"].splitlines()

    dirty_lines = [
        line
        for line in lines
        if line.strip() and not line.startswith("##")
    ]

    if dirty_lines:
        raise HTTPException(
            status_code=409,
            detail={
                "message": (
                    "Karen cannot begin a self-update while the "
                    "repository contains uncommitted changes."
                ),
                "changes": dirty_lines,
            },
        )


def _repository_relative_paths(
    record: CodingTaskRecord,
) -> list[str]:
    relative_paths: list[str] = []

    for action in record.plan.actions:
        prefix = "karen/"

        if not action.path.startswith(prefix):
            raise HTTPException(
                status_code=403,
                detail=f"Unsafe self-update path: {action.path}",
            )

        relative_path = action.path[len(prefix):]

        if not relative_path:
            raise HTTPException(
                status_code=403,
                detail="The repository root cannot be staged directly.",
            )

        relative_paths.append(relative_path)

    return sorted(set(relative_paths))


@router.get("/status")
def self_update_status() -> dict:
    return repository_status("karen")


@router.post(
    "/plan",
    response_model=CodingTaskRecord,
)
async def plan_self_update(
    request: SelfUpdateRequest,
) -> CodingTaskRecord:
    _assert_clean_repository()

    # Refresh the project index so newly created frontend files
    # are available to the local coding model.
    scan_project(
        ProjectScanRequest(
            path="karen",
            max_files=10_000,
            max_file_bytes=2_000_000,
        )
    )

    guarded_task = f"""
Update Karen's own source code safely.

Requirements:
- Preserve existing API compatibility unless explicitly requested.
- Do not modify .env, credentials, secrets, .git or .karen.
- Do not delete files.
- Keep changes focused on the requested feature.
- Include or update tests when backend behaviour changes.
- Every action path must begin with karen/.

USER REQUEST:
{request.task}
""".strip()

    coding_request = CodingTaskRequest(
        path="karen",
        task=guarded_task,
        model=request.model,
        max_context_files=request.max_context_files,
    )

    plan, context_files, selected_model = (
        await build_coding_plan(coding_request)
    )

    timestamp = _now()

    record = CodingTaskRecord(
        id=str(uuid4()),
        project_path="karen",
        task=request.task,
        model=selected_model,
        status="pending",
        context_files=context_files,
        plan=plan,
        created_at=timestamp,
        updated_at=timestamp,
    )

    save_task(record)
    return record


@router.post("/tasks/{task_id}/finalize")
def finalize_self_update(
    task_id: str,
    request: FinalizeSelfUpdateRequest,
) -> dict:
    if not request.confirm:
        raise HTTPException(
            status_code=409,
            detail="Finalizing a self-update requires confirm=true.",
        )

    record = load_task(task_id)

    if record.project_path != "karen":
        raise HTTPException(
            status_code=403,
            detail="This task is not a Karen self-update.",
        )

    if record.status != "completed":
        raise HTTPException(
            status_code=409,
            detail=(
                "Only a successfully completed task can be finalized. "
                f"Current status: {record.status}"
            ),
        )

    paths = _repository_relative_paths(record)

    stage_result = stage_paths(
        repository_path="karen",
        paths=paths,
        confirm=True,
    )

    message = request.message or (
        f"feat(self-update): {record.task[:140]}"
    )

    commit_result = commit_staged(
        repository_path="karen",
        message=message,
        confirm=True,
    )

    return {
        "task_id": task_id,
        "staging": stage_result,
        "commit": commit_result,
        "restart_required": True,
    }
