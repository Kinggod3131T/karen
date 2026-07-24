from __future__ import annotations

import json
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import HTTPException

from services.core.app.security.workspace import resolve_workspace_path


REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
AUDIT_LOG = REPOSITORY_ROOT / "logs" / "git-audit.jsonl"
BACKUP_ROOT_NAME = ".karen/backups"

BRANCH_PATTERN = re.compile(
    r"^(?![-./])(?!.*\.\.)(?!.*//)(?!.*@\{)"
    r"[A-Za-z0-9._/-]{1,100}(?<![/.])$"
)

PROTECTED_NAMES = {
    ".git",
    ".env",
    ".venv",
    "id_rsa",
    "id_ed25519",
}

PROTECTED_SUFFIXES = {
    ".pem",
    ".key",
    ".p12",
    ".pfx",
}


def _audit(operation: str, repository: Path, details: dict[str, Any]) -> None:
    AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)

    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "operation": operation,
        "repository": str(repository),
        **details,
    }

    with AUDIT_LOG.open("a", encoding="utf-8") as audit_file:
        audit_file.write(json.dumps(record) + "\n")


def _run_git(
    repository: Path,
    arguments: list[str],
    timeout: int = 30,
) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            ["git", "-C", str(repository), *arguments],
            capture_output=True,
            text=True,
            shell=False,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise HTTPException(
            status_code=504,
            detail="Git operation exceeded its timeout.",
        ) from exc


def resolve_repository(repository_path: str) -> Path:
    candidate = resolve_workspace_path(repository_path)

    if not candidate.is_dir():
        raise HTTPException(
            status_code=400,
            detail="Repository path is not a directory.",
        )

    result = _run_git(candidate, ["rev-parse", "--show-toplevel"])

    if result.returncode != 0:
        raise HTTPException(
            status_code=400,
            detail="The selected directory is not inside a Git repository.",
        )

    repository = Path(result.stdout.strip()).resolve()
    workspace = resolve_workspace_path(".").resolve()

    try:
        repository.relative_to(workspace)
    except ValueError as exc:
        raise HTTPException(
            status_code=403,
            detail="Git repository is outside Karen's workspace.",
        ) from exc

    return repository


def _validate_relative_path(repository: Path, path: str) -> str:
    supplied = Path(path)

    if supplied.is_absolute():
        raise HTTPException(
            status_code=403,
            detail="Git paths must be relative to the repository.",
        )

    resolved = (repository / supplied).resolve(strict=False)

    try:
        relative = resolved.relative_to(repository)
    except ValueError as exc:
        raise HTTPException(
            status_code=403,
            detail=f"Path escapes the repository: {path}",
        ) from exc

    if any(part in PROTECTED_NAMES for part in relative.parts):
        raise HTTPException(
            status_code=403,
            detail=f"Protected path cannot be modified: {path}",
        )

    if relative.suffix.lower() in PROTECTED_SUFFIXES:
        raise HTTPException(
            status_code=403,
            detail=f"Secret-like file cannot be modified: {path}",
        )

    return relative.as_posix()


def repository_status(repository_path: str) -> dict[str, Any]:
    repository = resolve_repository(repository_path)
    result = _run_git(
        repository,
        ["status", "--short", "--branch"],
    )

    return {
        "repository": str(repository),
        "return_code": result.returncode,
        "status": result.stdout,
        "stderr": result.stderr,
    }


def repository_diff(
    repository_path: str,
    staged: bool,
) -> dict[str, Any]:
    repository = resolve_repository(repository_path)
    arguments = ["diff"]

    if staged:
        arguments.append("--staged")

    result = _run_git(repository, arguments)

    return {
        "repository": str(repository),
        "staged": staged,
        "return_code": result.returncode,
        "diff": result.stdout[:50_000],
        "truncated": len(result.stdout) > 50_000,
        "stderr": result.stderr,
    }


def stage_paths(
    repository_path: str,
    paths: list[str],
    confirm: bool,
) -> dict[str, Any]:
    if not confirm:
        raise HTTPException(
            status_code=409,
            detail="Staging files requires confirm=true.",
        )

    repository = resolve_repository(repository_path)
    validated = [
        _validate_relative_path(repository, path)
        for path in paths
    ]

    result = _run_git(
        repository,
        ["add", "--", *validated],
    )

    if result.returncode != 0:
        raise HTTPException(
            status_code=400,
            detail=result.stderr or "Git staging failed.",
        )

    _audit(
        "stage",
        repository,
        {"paths": validated},
    )

    return {
        "repository": str(repository),
        "staged": validated,
        "success": True,
    }


def commit_staged(
    repository_path: str,
    message: str,
    confirm: bool,
) -> dict[str, Any]:
    if not confirm:
        raise HTTPException(
            status_code=409,
            detail="Creating a commit requires confirm=true.",
        )

    if "\n" in message or "\r" in message:
        raise HTTPException(
            status_code=400,
            detail="Commit message must be a single line.",
        )

    repository = resolve_repository(repository_path)

    staged_check = _run_git(
        repository,
        ["diff", "--cached", "--quiet"],
    )

    if staged_check.returncode == 0:
        raise HTTPException(
            status_code=409,
            detail="There are no staged changes to commit.",
        )

    if staged_check.returncode not in {0, 1}:
        raise HTTPException(
            status_code=400,
            detail=staged_check.stderr or "Unable to inspect staged changes.",
        )

    result = _run_git(
        repository,
        ["commit", "-m", message],
        timeout=60,
    )

    if result.returncode != 0:
        raise HTTPException(
            status_code=400,
            detail=result.stderr or result.stdout or "Commit failed.",
        )

    commit_id = _run_git(
        repository,
        ["rev-parse", "--short", "HEAD"],
    ).stdout.strip()

    _audit(
        "commit",
        repository,
        {
            "message": message,
            "commit": commit_id,
        },
    )

    return {
        "repository": str(repository),
        "commit": commit_id,
        "message": message,
        "output": result.stdout,
        "success": True,
    }


def create_branch(
    repository_path: str,
    branch: str,
    switch: bool,
    confirm: bool,
) -> dict[str, Any]:
    if not confirm:
        raise HTTPException(
            status_code=409,
            detail="Creating a branch requires confirm=true.",
        )

    if (
        not BRANCH_PATTERN.fullmatch(branch)
        or branch.endswith(".lock")
    ):
        raise HTTPException(
            status_code=400,
            detail="Invalid or unsafe Git branch name.",
        )

    repository = resolve_repository(repository_path)

    existing = _run_git(
        repository,
        ["show-ref", "--verify", f"refs/heads/{branch}"],
    )

    if existing.returncode == 0:
        raise HTTPException(
            status_code=409,
            detail="The branch already exists.",
        )

    if switch:
        dirty = _run_git(repository, ["status", "--porcelain"])

        if dirty.stdout.strip():
            raise HTTPException(
                status_code=409,
                detail=(
                    "Karen will not switch branches while the "
                    "working tree contains uncommitted changes."
                ),
            )

        arguments = ["switch", "-c", branch]
    else:
        arguments = ["branch", branch, "HEAD"]

    result = _run_git(repository, arguments)

    if result.returncode != 0:
        raise HTTPException(
            status_code=400,
            detail=result.stderr or "Branch creation failed.",
        )

    _audit(
        "create_branch",
        repository,
        {
            "branch": branch,
            "switched": switch,
        },
    )

    return {
        "repository": str(repository),
        "branch": branch,
        "switched": switch,
        "success": True,
    }


def create_checkpoint(
    repository_path: str,
    label: str | None,
    confirm: bool,
) -> dict[str, Any]:
    if not confirm:
        raise HTTPException(
            status_code=409,
            detail="Creating a checkpoint requires confirm=true.",
        )

    repository = resolve_repository(repository_path)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")

    safe_label = ""

    if label:
        safe_label = re.sub(
            r"[^A-Za-z0-9._-]+",
            "-",
            label.strip(),
        ).strip("-")[:40]

    tag_name = f"karen-checkpoint-{timestamp}"

    if safe_label:
        tag_name = f"{tag_name}-{safe_label}"

    result = _run_git(
        repository,
        ["tag", tag_name, "HEAD"],
    )

    if result.returncode != 0:
        raise HTTPException(
            status_code=400,
            detail=result.stderr or "Checkpoint creation failed.",
        )

    commit = _run_git(
        repository,
        ["rev-parse", "--short", "HEAD"],
    ).stdout.strip()

    _audit(
        "checkpoint",
        repository,
        {
            "tag": tag_name,
            "commit": commit,
        },
    )

    return {
        "repository": str(repository),
        "checkpoint": tag_name,
        "commit": commit,
        "success": True,
    }


def restore_paths(
    repository_path: str,
    paths: list[str],
    source: str,
    confirm: bool,
) -> dict[str, Any]:
    if not confirm:
        raise HTTPException(
            status_code=409,
            detail="Restoring files requires confirm=true.",
        )

    if source != "HEAD" and not source.startswith(
        "karen-checkpoint-"
    ):
        raise HTTPException(
            status_code=403,
            detail=(
                "Restore source must be HEAD or a Karen checkpoint."
            ),
        )

    repository = resolve_repository(repository_path)

    reference = _run_git(
        repository,
        ["rev-parse", "--verify", f"{source}^{{commit}}"],
    )

    if reference.returncode != 0:
        raise HTTPException(
            status_code=404,
            detail="Restore source does not exist.",
        )

    validated = [
        _validate_relative_path(repository, path)
        for path in paths
    ]

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_root = repository / BACKUP_ROOT_NAME / timestamp

    backed_up: list[str] = []

    for relative_path in validated:
        source_path = repository / relative_path

        if source_path.exists() and source_path.is_file():
            backup_path = backup_root / relative_path
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_path, backup_path)
            backed_up.append(relative_path)

    result = _run_git(
        repository,
        [
            "restore",
            "--source",
            source,
            "--worktree",
            "--",
            *validated,
        ],
    )

    if result.returncode != 0:
        raise HTTPException(
            status_code=400,
            detail=result.stderr or "Restore operation failed.",
        )

    _audit(
        "restore",
        repository,
        {
            "source": source,
            "paths": validated,
            "backed_up": backed_up,
            "backup_root": str(backup_root),
        },
    )

    return {
        "repository": str(repository),
        "source": source,
        "restored": validated,
        "backed_up": backed_up,
        "backup_directory": str(backup_root),
        "success": True,
    }
