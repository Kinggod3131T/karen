from fastapi import APIRouter

from services.core.app.schemas import CommandRequest, CommandResponse
from services.core.app.security.terminal import (
    command_allowlist,
    execute_safe_command,
)


router = APIRouter(
    prefix="/tools/terminal",
    tags=["Terminal tools"],
)


@router.get("/allowlist")
def allowlist() -> dict[str, list[str]]:
    return command_allowlist()


@router.post("/run", response_model=CommandResponse)
def run_command(request: CommandRequest) -> CommandResponse:
    return execute_safe_command(request)
