from typing import Any

from fastapi import APIRouter

from services.core.app.schemas import (
    GitBranchRequest,
    GitCheckpointRequest,
    GitCommitRequest,
    GitDiffRequest,
    GitRepositoryRequest,
    GitRestoreRequest,
    GitStageRequest,
)
from services.core.app.security.git_tools import (
    commit_staged,
    create_branch,
    create_checkpoint,
    repository_diff,
    repository_status,
    restore_paths,
    stage_paths,
)


router = APIRouter(
    prefix="/tools/git",
    tags=["Git tools"],
)


@router.post("/status")
def status(request: GitRepositoryRequest) -> dict[str, Any]:
    return repository_status(request.repository)


@router.post("/diff")
def diff(request: GitDiffRequest) -> dict[str, Any]:
    return repository_diff(
        repository_path=request.repository,
        staged=request.staged,
    )


@router.post("/stage")
def stage(request: GitStageRequest) -> dict[str, Any]:
    return stage_paths(
        repository_path=request.repository,
        paths=request.paths,
        confirm=request.confirm,
    )


@router.post("/commit")
def commit(request: GitCommitRequest) -> dict[str, Any]:
    return commit_staged(
        repository_path=request.repository,
        message=request.message,
        confirm=request.confirm,
    )


@router.post("/branch")
def branch(request: GitBranchRequest) -> dict[str, Any]:
    return create_branch(
        repository_path=request.repository,
        branch=request.branch,
        switch=request.switch,
        confirm=request.confirm,
    )


@router.post("/checkpoint")
def checkpoint(request: GitCheckpointRequest) -> dict[str, Any]:
    return create_checkpoint(
        repository_path=request.repository,
        label=request.label,
        confirm=request.confirm,
    )


@router.post("/restore")
def restore(request: GitRestoreRequest) -> dict[str, Any]:
    return restore_paths(
        repository_path=request.repository,
        paths=request.paths,
        source=request.source,
        confirm=request.confirm,
    )
