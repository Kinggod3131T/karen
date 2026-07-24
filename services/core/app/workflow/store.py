from pathlib import Path

from fastapi import HTTPException

from services.core.app.workflow.schemas import CodingTaskRecord


REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
TASK_DIRECTORY = REPOSITORY_ROOT / ".karen" / "tasks"


def _task_path(task_id: str) -> Path:
    if not task_id.replace("-", "").isalnum():
        raise HTTPException(
            status_code=400,
            detail="Invalid task ID.",
        )

    return TASK_DIRECTORY / f"{task_id}.json"


def save_task(record: CodingTaskRecord) -> None:
    TASK_DIRECTORY.mkdir(parents=True, exist_ok=True)

    _task_path(record.id).write_text(
        record.model_dump_json(indent=2),
        encoding="utf-8",
    )


def load_task(task_id: str) -> CodingTaskRecord:
    path = _task_path(task_id)

    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail="Coding task not found.",
        )

    return CodingTaskRecord.model_validate_json(
        path.read_text(encoding="utf-8")
    )


def list_tasks() -> list[CodingTaskRecord]:
    TASK_DIRECTORY.mkdir(parents=True, exist_ok=True)

    records: list[CodingTaskRecord] = []

    for path in TASK_DIRECTORY.glob("*.json"):
        try:
            records.append(
                CodingTaskRecord.model_validate_json(
                    path.read_text(encoding="utf-8")
                )
            )
        except (OSError, ValueError):
            continue

    return sorted(
        records,
        key=lambda record: record.created_at,
        reverse=True,
    )
