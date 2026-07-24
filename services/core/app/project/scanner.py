from __future__ import annotations

import hashlib
import json
import os
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from fastapi import HTTPException

from services.core.app.project.schemas import (
    ProjectFile,
    ProjectScanRequest,
    ProjectSummary,
)
from services.core.app.security.workspace import resolve_workspace_path


REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
INDEX_DIRECTORY = REPOSITORY_ROOT / ".karen" / "indexes"

IGNORED_DIRECTORIES = {
    ".git",
    ".idea",
    ".vscode",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".next",
    ".nuxt",
    "dist",
    "build",
    "coverage",
    "target",
    "vendor",
    "tmp",
    "temp",
    "logs",
    "postgres_data",
    "redis_data",
    "qdrant_storage",
}

MANIFEST_NAMES = {
    "package.json",
    "pnpm-lock.yaml",
    "package-lock.json",
    "yarn.lock",
    "requirements.txt",
    "pyproject.toml",
    "poetry.lock",
    "Pipfile",
    "go.mod",
    "go.sum",
    "Cargo.toml",
    "Cargo.lock",
    "pom.xml",
    "build.gradle",
    "build.gradle.kts",
    "Dockerfile",
    "compose.yaml",
    "compose.yml",
    "docker-compose.yaml",
    "docker-compose.yml",
    "Makefile",
}

ENTRYPOINT_NAMES = {
    "main.py",
    "app.py",
    "manage.py",
    "main.go",
    "main.rs",
    "main.ts",
    "main.js",
    "index.ts",
    "index.js",
    "server.ts",
    "server.js",
    "Program.cs",
    "Application.java",
}

LANGUAGE_BY_SUFFIX = {
    ".py": "Python",
    ".pyi": "Python",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".mjs": "JavaScript",
    ".cjs": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".go": "Go",
    ".java": "Java",
    ".kt": "Kotlin",
    ".kts": "Kotlin",
    ".rs": "Rust",
    ".c": "C",
    ".h": "C/C++",
    ".cc": "C++",
    ".cpp": "C++",
    ".hpp": "C++",
    ".cs": "C#",
    ".swift": "Swift",
    ".php": "PHP",
    ".rb": "Ruby",
    ".sh": "Shell",
    ".bash": "Shell",
    ".sql": "SQL",
    ".html": "HTML",
    ".css": "CSS",
    ".scss": "SCSS",
    ".vue": "Vue",
    ".svelte": "Svelte",
    ".json": "JSON",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".toml": "TOML",
    ".tf": "Terraform",
    ".md": "Markdown",
    ".xml": "XML",
}


def _language_for(path: Path) -> str:
    if path.name == "Dockerfile":
        return "Dockerfile"

    if path.name == "Makefile":
        return "Makefile"

    return LANGUAGE_BY_SUFFIX.get(path.suffix.lower(), "Other")


def _kind_for(path: Path) -> str:
    if path.name in MANIFEST_NAMES:
        return "manifest"

    if path.name in ENTRYPOINT_NAMES:
        return "entrypoint"

    if path.suffix.lower() in {
        ".py", ".js", ".jsx", ".ts", ".tsx",
        ".go", ".java", ".kt", ".rs", ".c",
        ".cpp", ".cs", ".swift", ".php", ".rb",
    }:
        return "source"

    if path.suffix.lower() in {
        ".json", ".yaml", ".yml", ".toml",
        ".xml", ".tf",
    }:
        return "configuration"

    if path.suffix.lower() == ".md":
        return "documentation"

    return "other"


def _is_git_repository(root: Path) -> bool:
    try:
        result = subprocess.run(
            [
                "git",
                "-C",
                str(root),
                "rev-parse",
                "--is-inside-work-tree",
            ],
            capture_output=True,
            text=True,
            shell=False,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False

    return result.returncode == 0 and result.stdout.strip() == "true"


def _read_small_text(path: Path, max_bytes: int) -> str:
    try:
        if path.stat().st_size > max_bytes:
            return ""

        return path.read_text(
            encoding="utf-8",
            errors="ignore",
        ).lower()
    except OSError:
        return ""


def _detect_frameworks(
    manifests: dict[str, str],
    files: list[ProjectFile],
) -> list[str]:
    frameworks: set[str] = set()

    package_json = manifests.get("package.json", "")

    js_markers = {
        '"next"': "Next.js",
        '"react"': "React",
        '"vue"': "Vue",
        '"@angular/core"': "Angular",
        '"svelte"': "Svelte",
        '"express"': "Express",
        '"fastify"': "Fastify",
        '"@nestjs/core"': "NestJS",
    }

    for marker, framework in js_markers.items():
        if marker in package_json:
            frameworks.add(framework)

    python_text = "\n".join(
        content
        for name, content in manifests.items()
        if name in {
            "requirements.txt",
            "pyproject.toml",
            "Pipfile",
        }
    )

    python_markers = {
        "fastapi": "FastAPI",
        "django": "Django",
        "flask": "Flask",
        "langchain": "LangChain",
        "pydantic": "Pydantic",
        "pytest": "Pytest",
    }

    for marker, framework in python_markers.items():
        if marker in python_text:
            frameworks.add(framework)

    go_mod = manifests.get("go.mod", "")

    if "github.com/gin-gonic/gin" in go_mod:
        frameworks.add("Gin")

    if "github.com/gofiber/fiber" in go_mod:
        frameworks.add("Fiber")

    cargo = manifests.get("Cargo.toml", "")

    if "actix-web" in cargo:
        frameworks.add("Actix Web")

    if "axum" in cargo:
        frameworks.add("Axum")

    paths = {file.path for file in files}

    if any(Path(path).name == "Dockerfile" for path in paths):
        frameworks.add("Docker")

    if any(
        Path(path).name in {
            "compose.yaml",
            "compose.yml",
            "docker-compose.yaml",
            "docker-compose.yml",
        }
        for path in paths
    ):
        frameworks.add("Docker Compose")

    if any(path.endswith(".tf") for path in paths):
        frameworks.add("Terraform")

    if any(
        path.startswith("kubernetes/")
        or "/kubernetes/" in path
        or path.startswith("k8s/")
        or "/k8s/" in path
        for path in paths
    ):
        frameworks.add("Kubernetes")

    return sorted(frameworks)


def scan_project(request: ProjectScanRequest) -> ProjectSummary:
    root = resolve_workspace_path(request.path)

    if not root.exists():
        raise HTTPException(
            status_code=404,
            detail="Project path does not exist.",
        )

    if not root.is_dir():
        raise HTTPException(
            status_code=400,
            detail="Project path is not a directory.",
        )

    files: list[ProjectFile] = []
    language_counts: Counter[str] = Counter()
    manifests: list[str] = []
    entrypoints: list[str] = []
    manifest_contents: dict[str, str] = {}

    total_bytes = 0
    truncated = False

    for current_root, directories, filenames in os.walk(
        root,
        topdown=True,
        followlinks=False,
    ):
        current_path = Path(current_root)

        directories[:] = [
            directory
            for directory in directories
            if (
                directory not in IGNORED_DIRECTORIES
                and not (current_path / directory).is_symlink()
            )
        ]

        for filename in sorted(filenames):
            if len(files) >= request.max_files:
                truncated = True
                break

            absolute_path = current_path / filename

            if absolute_path.is_symlink():
                continue

            try:
                stat = absolute_path.stat()
            except OSError:
                continue

            if not absolute_path.is_file():
                continue

            relative_path = absolute_path.relative_to(root)

            language = _language_for(absolute_path)
            kind = _kind_for(absolute_path)

            record = ProjectFile(
                path=relative_path.as_posix(),
                size=stat.st_size,
                language=language,
                kind=kind,
            )

            files.append(record)
            total_bytes += stat.st_size
            language_counts[language] += 1

            if absolute_path.name in MANIFEST_NAMES:
                manifests.append(record.path)
                manifest_contents.setdefault(
                    absolute_path.name,
                    _read_small_text(
                        absolute_path,
                        request.max_file_bytes,
                    ),
                )

            if absolute_path.name in ENTRYPOINT_NAMES:
                entrypoints.append(record.path)

        if truncated:
            break

    frameworks = _detect_frameworks(
        manifest_contents,
        files,
    )

    index_id = hashlib.sha256(
        str(root).encode("utf-8")
    ).hexdigest()[:16]

    summary = ProjectSummary(
        index_id=index_id,
        root=str(root),
        name=root.name,
        git_repository=_is_git_repository(root),
        total_files=len(files),
        total_bytes=total_bytes,
        truncated=truncated,
        languages=dict(language_counts.most_common()),
        frameworks=frameworks,
        manifests=sorted(manifests),
        entrypoints=sorted(entrypoints),
        ignored_directories=sorted(IGNORED_DIRECTORIES),
        sample_files=files[:100],
        indexed_at=datetime.now(timezone.utc).isoformat(),
    )

    INDEX_DIRECTORY.mkdir(parents=True, exist_ok=True)

    index_path = INDEX_DIRECTORY / f"{index_id}.json"

    index_path.write_text(
        json.dumps(
            {
                "summary": summary.model_dump(),
                "files": [
                    record.model_dump()
                    for record in files
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    return summary


def list_indexes() -> list[dict[str, str]]:
    INDEX_DIRECTORY.mkdir(parents=True, exist_ok=True)

    indexes: list[dict[str, str]] = []

    for index_path in sorted(
        INDEX_DIRECTORY.glob("*.json"),
        reverse=True,
    ):
        try:
            data = json.loads(
                index_path.read_text(encoding="utf-8")
            )

            summary = data.get("summary", {})

            indexes.append(
                {
                    "index_id": index_path.stem,
                    "name": str(summary.get("name", "")),
                    "root": str(summary.get("root", "")),
                    "indexed_at": str(
                        summary.get("indexed_at", "")
                    ),
                }
            )
        except (OSError, ValueError, TypeError):
            continue

    return indexes
