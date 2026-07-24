from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from services.core.app.security.git_tools import (
    resolve_repository,
)
from services.core.app.workflow.schemas import (
    VerificationResult,
)


MAX_OUTPUT = 15_000


def _truncate(value: str) -> str:
    if len(value) <= MAX_OUTPUT:
        return value

    return value[:MAX_OUTPUT] + "\n[Output truncated by Karen.]"


def _run(
    repository: Path,
    name: str,
    command: list[str],
    timeout: int,
) -> VerificationResult:
    try:
        result = subprocess.run(
            command,
            cwd=repository,
            capture_output=True,
            text=True,
            shell=False,
            timeout=timeout,
            check=False,
        )

        return VerificationResult(
            name=name,
            command=command,
            return_code=result.returncode,
            stdout=_truncate(result.stdout),
            stderr=_truncate(result.stderr),
            passed=result.returncode == 0,
            timed_out=False,
        )

    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout or ""
        stderr = exc.stderr or ""

        if isinstance(stdout, bytes):
            stdout = stdout.decode("utf-8", errors="replace")

        if isinstance(stderr, bytes):
            stderr = stderr.decode("utf-8", errors="replace")

        return VerificationResult(
            name=name,
            command=command,
            return_code=124,
            stdout=_truncate(stdout),
            stderr=_truncate(stderr),
            passed=False,
            timed_out=True,
        )


def run_verification(
    repository_path: str,
) -> list[VerificationResult]:
    repository = resolve_repository(repository_path)
    results: list[VerificationResult] = []

    compile_targets = [
        directory
        for directory in (
            "services",
            "apps",
            "src",
            "tests",
        )
        if (repository / directory).is_dir()
    ]

    if compile_targets:
        results.append(
            _run(
                repository=repository,
                name="compileall",
                command=[
                    sys.executable,
                    "-m",
                    "compileall",
                    "-q",
                    *compile_targets,
                ],
                timeout=60,
            )
        )

    if (repository / "tests").is_dir():
        results.append(
            _run(
                repository=repository,
                name="pytest",
                command=[
                    sys.executable,
                    "-m",
                    "pytest",
                    "-q",
                ],
                timeout=120,
            )
        )

    return results
