from fastapi import FastAPI

from services.core.app.routes import (
    agent,
    ai,
    files,
    git,
    project,
    system,
    terminal,
)
from services.core.app.settings import settings


app = FastAPI(
    title=settings.app_name,
    version="0.8.0",
    description=(
        "Local-first AI workstation orchestration service "
        "with approval-gated tools and project intelligence."
    ),
)

app.include_router(system.router)
app.include_router(ai.router)
app.include_router(files.router)
app.include_router(agent.router)
app.include_router(terminal.router)
app.include_router(git.router)
app.include_router(project.router)
