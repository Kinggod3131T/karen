from typing import Any

from fastapi import APIRouter

from services.core.app.project.context import (
    select_project_context,
)
from services.core.app.project.scanner import (
    list_indexes,
    scan_project,
)
from services.core.app.project.schemas import (
    ProjectContext,
    ProjectContextRequest,
    ProjectScanRequest,
    ProjectSummary,
)


router = APIRouter(
    prefix="/project",
    tags=["Project intelligence"],
)


@router.post("/scan", response_model=ProjectSummary)
def scan(request: ProjectScanRequest) -> ProjectSummary:
    return scan_project(request)


@router.get("/indexes")
def indexes() -> list[dict[str, Any]]:
    return list_indexes()


@router.post("/context", response_model=ProjectContext)
def context(
    request: ProjectContextRequest,
) -> ProjectContext:
    return select_project_context(request)
