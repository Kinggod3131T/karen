from pathlib import Path

from fastapi import HTTPException

from services.core.app.settings import settings


def resolve_workspace_path(user_path: str) -> Path:
    workspace = settings.karen_workspace.expanduser().resolve()
    requested = Path(user_path).expanduser()

    if not requested.is_absolute():
        requested = workspace / requested

    resolved = requested.resolve(strict=False)

    try:
        resolved.relative_to(workspace)
    except ValueError as exc:
        raise HTTPException(
            status_code=403,
            detail="Access outside the configured workspace is forbidden.",
        ) from exc

    return resolved
