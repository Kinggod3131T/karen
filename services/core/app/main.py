from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from services.core.app.routes import (
    agent,
    ai,
    files,
    git,
    project,
    self_update,
    system,
    terminal,
    workflow,
)
from services.core.app.settings import settings


app = FastAPI(
    title=settings.app_name,
    version="1.1.0",
    description=(
        "Local-first coding agent with project intelligence, "
        "approval-gated execution, verification, AI review "
        "and controlled self-updates."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(system.router)
app.include_router(ai.router)
app.include_router(files.router)
app.include_router(agent.router)
app.include_router(terminal.router)
app.include_router(git.router)
app.include_router(project.router)
app.include_router(workflow.router)
app.include_router(self_update.router)
