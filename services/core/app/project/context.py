from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import HTTPException

from services.core.app.project.scanner import (
    INDEX_DIRECTORY,
    scan_project,
)
from services.core.app.project.schemas import (
    ContextFile,
    ProjectContext,
    ProjectContextRequest,
    ProjectScanRequest,
)
from services.core.app.security.workspace import resolve_workspace_path


TOKEN_PATTERN = re.compile(r"[A-Za-z][A-Za-z0-9_.-]{1,}")

STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by",
    "can", "create", "do", "for", "from", "how", "in",
    "into", "is", "it", "of", "on", "or", "please",
    "that", "the", "this", "to", "use", "with",
}

TEXT_SUFFIXES = {
    ".py", ".pyi",
    ".js", ".jsx", ".mjs", ".cjs",
    ".ts", ".tsx",
    ".go", ".java", ".kt", ".kts",
    ".rs", ".c", ".h", ".cc", ".cpp", ".hpp",
    ".cs", ".swift", ".php", ".rb",
    ".sh", ".bash", ".zsh",
    ".sql",
    ".html", ".css", ".scss",
    ".vue", ".svelte",
    ".json", ".yaml", ".yml", ".toml", ".tf",
    ".md", ".txt", ".xml",
}

SAFE_NAME_WITHOUT_SUFFIX = {
    "Dockerfile",
    "Makefile",
    "Procfile",
}

EXCLUDED_NAMES = {
    ".env",
    ".env.local",
    ".env.production",
    ".env.development",
    "credentials.json",
    "secrets.json",
    "id_rsa",
    "id_ed25519",
}

EXCLUDED_SUFFIXES = {
    ".pem",
    ".key",
    ".p12",
    ".pfx",
    ".crt",
    ".cer",
    ".der",
    ".sqlite",
    ".sqlite3",
    ".db",
    ".lock",
}

KIND_SCORE = {
    "entrypoint": 9.0,
    "manifest": 7.0,
    "source": 5.0,
    "configuration": 4.0,
    "documentation": 2.0,
    "other": 0.5,
}


def _project_index_id(root: Path) -> str:
    return hashlib.sha256(
        str(root).encode("utf-8")
    ).hexdigest()[:16]


def _tokens(value: str) -> set[str]:
    return {
        token.lower()
        for token in TOKEN_PATTERN.findall(value)
        if token.lower() not in STOP_WORDS
    }


def _is_safe_text_path(path: Path) -> bool:
    if path.name in EXCLUDED_NAMES:
        return False

    if path.suffix.lower() in EXCLUDED_SUFFIXES:
        return False

    if path.name in SAFE_NAME_WITHOUT_SUFFIX:
        return True

    return path.suffix.lower() in TEXT_SUFFIXES


def _load_or_create_index(
    project_path: str,
) -> tuple[Path, str, dict[str, Any]]:
    root = resolve_workspace_path(project_path)

    if not root.exists() or not root.is_dir():
        raise HTTPException(
            status_code=404,
            detail="Project directory does not exist.",
        )

    index_id = _project_index_id(root)
    index_path = INDEX_DIRECTORY / f"{index_id}.json"

    if not index_path.exists():
        scan_project(
            ProjectScanRequest(
                path=project_path,
                max_files=5000,
                max_file_bytes=2_000_000,
            )
        )

    try:
        data = json.loads(
            index_path.read_text(encoding="utf-8")
        )
    except (OSError, ValueError) as exc:
        raise HTTPException(
            status_code=500,
            detail="The project index could not be loaded.",
        ) from exc

    return root, index_id, data


def _read_file(
    path: Path,
    character_limit: int,
) -> tuple[str, bool]:
    try:
        text = path.read_text(
            encoding="utf-8",
            errors="ignore",
        )
    except OSError:
        return "", False

    if len(text) <= character_limit:
        return text, False

    return text[:character_limit], True


def _score_file(
    relative_path: str,
    kind: str,
    language: str,
    task_tokens: set[str],
    content_preview: str,
    manifests: set[str],
    entrypoints: set[str],
) -> tuple[float, list[str]]:
    path_tokens = _tokens(relative_path)
    content_tokens = _tokens(content_preview[:5000])

    score = KIND_SCORE.get(kind, 0.0)
    reasons: list[str] = []

    path_matches = task_tokens & path_tokens
    content_matches = task_tokens & content_tokens

    if path_matches:
        score += len(path_matches) * 7.0
        reasons.append(
            "task terms matched path: "
            + ", ".join(sorted(path_matches))
        )

    if content_matches:
        score += min(len(content_matches), 10) * 2.0
        reasons.append(
            "task terms matched content: "
            + ", ".join(sorted(content_matches)[:10])
        )

    if relative_path in entrypoints:
        score += 5.0
        reasons.append("project entry point")

    if relative_path in manifests:
        score += 4.0
        reasons.append("project manifest")

    task_text = " ".join(task_tokens)

    language_markers = {
        "python": "python",
        "fastapi": "python",
        "typescript": "typescript",
        "javascript": "javascript",
        "react": "typescript",
        "next": "typescript",
        "golang": "go",
        "go": "go",
        "java": "java",
        "rust": "rust",
        "docker": "dockerfile",
        "terraform": "terraform",
        "yaml": "yaml",
    }

    for task_marker, expected_language in language_markers.items():
        if (
            task_marker in task_text
            and expected_language in language.lower()
        ):
            score += 4.0
            reasons.append(
                f"language matches requested {task_marker} work"
            )

    if kind in KIND_SCORE:
        reasons.append(f"{kind} file")

    return score, reasons


def select_project_context(
    request: ProjectContextRequest,
) -> ProjectContext:
    root, index_id, index_data = _load_or_create_index(
        request.path
    )

    summary = index_data.get("summary", {})
    indexed_files = index_data.get("files", [])

    task_tokens = _tokens(request.task)
    manifests = set(summary.get("manifests", []))
    entrypoints = set(summary.get("entrypoints", []))

    candidates: list[dict[str, Any]] = []

    for record in indexed_files:
        relative_path = str(record.get("path", ""))
        absolute_path = (root / relative_path).resolve(
            strict=False
        )

        try:
            absolute_path.relative_to(root)
        except ValueError:
            continue

        if (
            not absolute_path.exists()
            or not absolute_path.is_file()
            or absolute_path.is_symlink()
            or not _is_safe_text_path(absolute_path)
        ):
            continue

        content, truncated = _read_file(
            absolute_path,
            request.max_chars_per_file,
        )

        if not content.strip():
            continue

        score, reasons = _score_file(
            relative_path=relative_path,
            kind=str(record.get("kind", "other")),
            language=str(record.get("language", "Other")),
            task_tokens=task_tokens,
            content_preview=content,
            manifests=manifests,
            entrypoints=entrypoints,
        )

        candidates.append(
            {
                "path": relative_path,
                "language": str(
                    record.get("language", "Other")
                ),
                "kind": str(record.get("kind", "other")),
                "score": score,
                "reasons": reasons,
                "content": content,
                "truncated": truncated,
            }
        )

    candidates.sort(
        key=lambda item: (
            item["score"],
            -len(item["content"]),
        ),
        reverse=True,
    )

    selected: list[ContextFile] = []
    total_characters = 0

    for candidate in candidates:
        if len(selected) >= request.max_files:
            break

        remaining = (
            request.max_total_chars - total_characters
        )

        if remaining <= 0:
            break

        content = candidate["content"]
        truncated = candidate["truncated"]

        if len(content) > remaining:
            content = content[:remaining]
            truncated = True

        if not content:
            continue

        selected.append(
            ContextFile(
                path=candidate["path"],
                language=candidate["language"],
                kind=candidate["kind"],
                score=round(candidate["score"], 2),
                reasons=candidate["reasons"],
                content=content,
                truncated=truncated,
            )
        )

        total_characters += len(content)

    return ProjectContext(
        index_id=index_id,
        project_root=str(root),
        task=request.task,
        selected_files=selected,
        total_characters=total_characters,
        generated_at=datetime.now(
            timezone.utc
        ).isoformat(),
    )
