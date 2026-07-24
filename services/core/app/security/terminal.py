from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import HTTPException

from services.core.app.schemas import CommandRequest, CommandResponse
from services.core.app.security.workspace import resolve_workspace_path


MAX_OUTPUT_CHARACTERS = 20_000

REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
AUDIT_LOG = REPOSITORY_ROOT / "logs" / "terminal-audit.jsonl"


def command_allowlist() -> dict[str, list[str]]:
    return {
        "pwd": ["pwd"],
        "ls": [
            "ls",
            "ls -l",
            "ls -la",
            "ls -lah",
        ],
        "git": [
            "git status",
            "git status --short",
            "git diff",
            "git diff --staged",
            "git log --oneline",
            "git log --oneline -n <1-50>",
            "git branch --show-current",
            "git rev-parse --show-toplevel",
        ],
        "docker": [
            "docker ps",
            "docker ps -a",
            "docker images",
            "docker compose ps",
        ],
        "versions": [
            "python --version",
            "go version",
            "node --version",
            "npm --version",
            "pnpm --version",
        ],
        "ollama": [
            "ollama list",
        ],
    }


def _truncate(value: str | bytes | None) -> str:
    if value is None:
        return ""

    if isinstance(value, bytes):
        value = value.decode("utf-8", errors="replace")

    if len(value) <= MAX_OUTPUT_CHARACTERS:
        return value

    return (
        value[:MAX_OUTPUT_CHARACTERS]
        + "\n\n[Karen truncated the remaining output.]"
    )


def _validate_ls(arguments: list[str]) -> None:
    allowed = {
        (),
        ("-l",),
        ("-la",),
        ("-lah",),
        ("-al",),
        ("-alh",),
    }

    if tuple(arguments) not in allowed:
        raise HTTPException(
            status_code=403,
            detail="This ls argument combination is not allowed.",
        )


def _validate_git(arguments: list[str]) -> None:
    allowed_exact = {
        ("status",),
        ("status", "--short"),
        ("diff",),
        ("diff", "--staged"),
        ("log", "--oneline"),
        ("branch", "--show-current"),
        ("rev-parse", "--show-toplevel"),
    }

    argument_tuple = tuple(arguments)

    if argument_tuple in allowed_exact:
        return

    if (
        len(arguments) == 4
        and arguments[0:3] == ["log", "--oneline", "-n"]
    ):
        try:
            limit = int(arguments[3])
        except ValueError as exc:
            raise HTTPException(
                status_code=403,
                detail="Git log limit must be an integer.",
            ) from exc

        if 1 <= limit <= 50:
            return

    raise HTTPException(
        status_code=403,
        detail="This Git command is not in Karen's read-only allowlist.",
    )


def _validate_docker(arguments: list[str]) -> None:
    allowed = {
        ("ps",),
        ("ps", "-a"),
        ("images",),
        ("compose", "ps"),
    }

    if tuple(arguments) not in allowed:
        raise HTTPException(
            status_code=403,
            detail="This Docker command is not in Karen's allowlist.",
        )


def _validate_version_command(
    executable: str,
    arguments: list[str],
) -> None:
    expected_arguments = {
        "python": ["--version"],
        "node": ["--version"],
        "npm": ["--version"],
        "pnpm": ["--version"],
        "go": ["version"],
    }

    if arguments != expected_arguments[executable]:
        raise HTTPException(
            status_code=403,
            detail=f"Only the version command is allowed for {executable}.",
        )


def _validate_command(argv: list[str]) -> None:
    executable = argv[0]
    arguments = argv[1:]

    if Path(executable).name != executable:
        raise HTTPException(
            status_code=403,
            detail="Executable paths are not allowed.",
        )

    if executable == "pwd":
        if arguments:
            raise HTTPException(
                status_code=403,
                detail="pwd does not accept arguments.",
            )
        return

    if executable == "ls":
        _validate_ls(arguments)
        return

    if executable == "git":
        _validate_git(arguments)
        return

    if executable == "docker":
        _validate_docker(arguments)
        return

    if executable in {"python", "go", "node", "npm", "pnpm"}:
        _validate_version_command(executable, arguments)
        return

    if executable == "ollama" and arguments == ["list"]:
        return

    raise HTTPException(
        status_code=403,
        detail=f"Command '{executable}' is not allowed.",
    )


def _safe_environment() -> dict[str, str]:
    allowed_keys = {
        "PATH",
        "HOME",
        "LANG",
        "LC_ALL",
        "TERM",
        "USER",
    }

    environment = {
        key: value
        for key, value in os.environ.items()
        if key in allowed_keys
    }

    environment["PYTHONUNBUFFERED"] = "1"
    return environment


def _write_audit_record(record: dict[str, Any]) -> None:
    AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)

    with AUDIT_LOG.open("a", encoding="utf-8") as audit_file:
        audit_file.write(json.dumps(record) + "\n")


def execute_safe_command(
    request: CommandRequest,
) -> CommandResponse:
    if not request.confirm:
        raise HTTPException(
            status_code=409,
            detail="Command execution requires confirm=true.",
        )

    _validate_command(request.argv)

    working_directory = resolve_workspace_path(request.cwd)

    if not working_directory.exists():
        raise HTTPException(
            status_code=404,
            detail="Working directory does not exist.",
        )

    if not working_directory.is_dir():
        raise HTTPException(
            status_code=400,
            detail="Working directory is not a directory.",
        )

    started_at = datetime.now(timezone.utc).isoformat()

    try:
        completed = subprocess.run(
            request.argv,
            cwd=working_directory,
            env=_safe_environment(),
            capture_output=True,
            text=True,
            shell=False,
            timeout=request.timeout_seconds,
            check=False,
        )

        response = CommandResponse(
            argv=request.argv,
            cwd=str(working_directory),
            return_code=completed.returncode,
            stdout=_truncate(completed.stdout),
            stderr=_truncate(completed.stderr),
            timed_out=False,
        )

    except subprocess.TimeoutExpired as exc:
        response = CommandResponse(
            argv=request.argv,
            cwd=str(working_directory),
            return_code=124,
            stdout=_truncate(exc.stdout),
            stderr=_truncate(exc.stderr),
            timed_out=True,
        )

    _write_audit_record(
        {
            "timestamp": started_at,
            "argv": response.argv,
            "cwd": response.cwd,
            "return_code": response.return_code,
            "timed_out": response.timed_out,
        }
    )

    return response
