from typing import Any

from fastapi import APIRouter

from services.core.app.schemas import FilePathRequest, FileWriteRequest
from services.core.app.tools.filesystem import (
    list_directory,
    read_text_file,
    write_text_file,
)


router = APIRouter(prefix="/tools/files", tags=["File tools"])


@router.post("/list")
def list_path(request: FilePathRequest) -> dict[str, Any]:
    return list_directory(request.path)


@router.post("/read")
def read_file(request: FilePathRequest) -> dict[str, str]:
    return read_text_file(request.path)


@router.post("/write")
def write_file(request: FileWriteRequest) -> dict[str, Any]:
    return write_text_file(
        path=request.path,
        content=request.content,
        confirm=request.confirm,
    )
