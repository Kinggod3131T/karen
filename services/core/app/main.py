from fastapi import FastAPI

from services.core.app.routes import (
    agent,
    ai,
    files,
    git,
    project,
    system,
    terminal,
    workflow,
)
from services.core.app.settings import settings


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description=(
        "Local-first coding agent with project intelligence, "
        "approval-gated execution, verification and AI review."
    ),
)

app.include_router(system.router)
app.include_router(ai.router)
app.include_router(files.router)
app.include_router(agent.router)
app.include_router(terminal.router)
app.include_router(git.router)
app.include_router(project.router)
app.include_router(workflow.router)
