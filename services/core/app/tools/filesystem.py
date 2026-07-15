from pathlib import Path
from typing import Any

from fastapi import HTTPException

from services.core.app.security.workspace import resolve_workspace_path


def list_directory(path: str) -> dict[str, Any]:
    resolved = resolve_workspace_path(path)

    if not resolved.exists():
        raise HTTPException(status_code=404, detail="Path does not exist.")

    if not resolved.is_dir():
        raise HTTPException(status_code=400, detail="Path is not a directory.")

    entries = []

    for item in sorted(resolved.iterdir(), key=lambda entry: entry.name.lower()):
        entries.append(
            {
                "name": item.name,
                "path": str(item),
                "type": "directory" if item.is_dir() else "file",
                "size": item.stat().st_size if item.is_file() else None,
            }
        )

    return {
        "path": str(resolved),
        "entries": entries,
    }


def read_text_file(path: str) -> dict[str, str]:
    resolved = resolve_workspace_path(path)

    if not resolved.exists():
        raise HTTPException(status_code=404, detail="File does not exist.")

    if not resolved.is_file():
        raise HTTPException(status_code=400, detail="Path is not a file.")

    if resolved.stat().st_size > 2_000_000:
        raise HTTPException(
            status_code=413,
            detail="File exceeds the 2 MB reading limit.",
        )

    try:
        content = resolved.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise HTTPException(
            status_code=415,
            detail="Only UTF-8 text files are supported.",
        ) from exc

    return {
        "path": str(resolved),
        "content": content,
    }


def write_text_file(path: str, content: str, confirm: bool) -> dict[str, Any]:
    if not confirm:
        raise HTTPException(
            status_code=409,
            detail="Writing requires confirm=true.",
        )

    resolved = resolve_workspace_path(path)
    resolved.parent.mkdir(parents=True, exist_ok=True)

    previous_content: str | None = None

    if resolved.exists():
        if not resolved.is_file():
            raise HTTPException(
                status_code=400,
                detail="Target path is not a regular file.",
            )

        try:
            previous_content = resolved.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            previous_content = None

        backup_path = resolved.with_suffix(resolved.suffix + ".karen-backup")
        backup_path.write_bytes(resolved.read_bytes())

    resolved.write_text(content, encoding="utf-8")

    return {
        "path": str(resolved),
        "written": True,
        "created": previous_content is None,
        "backup_created": previous_content is not None,
    }
