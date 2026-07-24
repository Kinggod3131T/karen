from fastapi import FastAPI

from services.core.app.routes import agent, ai, files, system
from services.core.app.settings import settings


app = FastAPI(
    title=settings.app_name,
    version="0.4.0",
    description=(
        "Local-first AI workstation orchestration service "
        "with approval-gated tools."
    ),
)

app.include_router(system.router)
app.include_router(ai.router)
app.include_router(files.router)
app.include_router(agent.router)
