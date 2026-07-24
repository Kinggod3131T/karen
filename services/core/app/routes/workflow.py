from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, HTTPException

from services.core.app.security.git_tools import (
    create_checkpoint,
    repository_diff,
)
from services.core.app.workflow.executor import (
    execute_project_actions,
)
from services.core.app.workflow.planner import (
    build_coding_plan,
)
from services.core.app.workflow.reviewer import (
    review_changes,
)
from services.core.app.workflow.schemas import (
    CodingTaskRecord,
    CodingTaskRequest,
)
from services.core.app.workflow.store import (
    list_tasks,
    load_task,
    save_task,
)
from services.core.app.workflow.verification import (
    run_verification,
)


router = APIRouter(
    prefix="/workflow",
    tags=["Coding workflow"],
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@router.post(
    "/tasks",
    response_model=CodingTaskRecord,
)
async def create_task(
    request: CodingTaskRequest,
) -> CodingTaskRecord:
    plan, context_files, selected_model = (
        await build_coding_plan(request)
    )

    timestamp = _now()

    record = CodingTaskRecord(
        id=str(uuid4()),
        project_path=request.path,
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


@router.get(
    "/tasks",
    response_model=list[CodingTaskRecord],
)
def tasks() -> list[CodingTaskRecord]:
    return list_tasks()


@router.get(
    "/tasks/{task_id}",
    response_model=CodingTaskRecord,
)
def task(task_id: str) -> CodingTaskRecord:
    return load_task(task_id)


@router.post(
    "/tasks/{task_id}/approve",
    response_model=CodingTaskRecord,
)
async def approve_task(
    task_id: str,
) -> CodingTaskRecord:
    record = load_task(task_id)

    if record.status != "pending":
        raise HTTPException(
            status_code=409,
            detail=(
                "Only pending tasks can be approved. "
                f"Current status: {record.status}"
            ),
        )

    record.status = "running"
    record.updated_at = _now()
    save_task(record)

    try:
        checkpoint = create_checkpoint(
            repository_path=record.project_path,
            label=f"task-{record.id[:8]}",
            confirm=True,
        )

        record.checkpoint = checkpoint["checkpoint"]

        record.action_results = execute_project_actions(
            project_path=record.project_path,
            actions=record.plan.actions,
        )

        record.verification_results = run_verification(
            repository_path=record.project_path,
        )

        diff_result = repository_diff(
            repository_path=record.project_path,
            staged=False,
        )

        record.review = await review_changes(
            task=record.task,
            plan=record.plan,
            diff=diff_result.get("diff", ""),
            verification=record.verification_results,
            model=record.model,
        )

        verification_passed = (
            bool(record.verification_results)
            and all(
                result.passed
                for result in record.verification_results
            )
        )

        if (
            verification_passed
            and record.review.verdict == "approved"
        ):
            record.status = "completed"
        else:
            record.status = "needs_review"

    except Exception as exc:
        record.status = "failed"
        record.error = str(exc)
        record.updated_at = _now()
        save_task(record)

        if isinstance(exc, HTTPException):
            raise

        raise HTTPException(
            status_code=500,
            detail=f"Coding workflow failed: {exc}",
        ) from exc

    record.updated_at = _now()
    save_task(record)

    return record


@router.post(
    "/tasks/{task_id}/reject",
    response_model=CodingTaskRecord,
)
def reject_task(task_id: str) -> CodingTaskRecord:
    record = load_task(task_id)

    if record.status != "pending":
        raise HTTPException(
            status_code=409,
            detail=(
                "Only pending tasks can be rejected. "
                f"Current status: {record.status}"
            ),
        )

    record.status = "rejected"
    record.updated_at = _now()
    save_task(record)

    return record
