from typing import Any

from fastapi import HTTPException

from services.core.app.agent.executor import execute_actions
from services.core.app.schemas import PlannedAction
from services.core.app.security.workspace import (
    resolve_workspace_path,
)


PROTECTED_PARTS = {
    ".git",
    ".venv",
    ".karen",
    "__pycache__",
    "logs",
}

PROTECTED_NAMES = {
    ".env",
    ".env.local",
    ".env.production",
    "credentials.json",
    "secrets.json",
    "id_rsa",
    "id_ed25519",
}

PROTECTED_SUFFIXES = {
    ".pem",
    ".key",
    ".p12",
    ".pfx",
}


def execute_project_actions(
    project_path: str,
    actions: list[PlannedAction],
) -> list[dict[str, Any]]:
    project_root = resolve_workspace_path(project_path).resolve()

    if not project_root.exists() or not project_root.is_dir():
        raise HTTPException(
            status_code=404,
            detail="Project directory does not exist.",
        )

    for action in actions:
        target = resolve_workspace_path(action.path).resolve()

        try:
            relative = target.relative_to(project_root)
        except ValueError as exc:
            raise HTTPException(
                status_code=403,
                detail=(
                    f"Action escapes the selected project: "
                    f"{action.path}"
                ),
            ) from exc

        if any(part in PROTECTED_PARTS for part in relative.parts):
            raise HTTPException(
                status_code=403,
                detail=f"Protected path rejected: {action.path}",
            )

        if (
            relative.name in PROTECTED_NAMES
            or relative.name.startswith(".env.")
            or relative.suffix.lower() in PROTECTED_SUFFIXES
        ):
            raise HTTPException(
                status_code=403,
                detail=f"Secret-like path rejected: {action.path}",
            )

    return execute_actions(actions)
